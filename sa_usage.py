#!/usr/bin/env python
import argparse
import datetime
import json
import sys
import time

import googleapiclient.discovery
from google.cloud import monitoring_v3
from google.oauth2 import service_account


def get_service_accounts(project_id):
    service = googleapiclient.discovery.build("iam", "v1")

    result = (
        service.projects()
        .serviceAccounts()
        .list(name="projects/{project_id}".format(project_id=project_id))
        .execute()
    )

    service_accounts = dict()
    for sa in result.get("accounts"):
        service_account_id = sa["uniqueId"]
        service_account_keys = {
            key: 0 for key in get_service_account_keys(project_id, service_account_id)
        }
        service_accounts[service_account_id] = {
            "displayName": sa["displayName"],
            "email": sa["email"],
            "keys": service_account_keys,
            "totalUses": 0,
        }

    return service_accounts


def get_service_account_keys(project_id, service_account_id):
    service = googleapiclient.discovery.build("iam", "v1")

    result = (
        service.projects()
        .serviceAccounts()
        .keys()
        .list(
            name="projects/{project_id}/serviceAccounts/{service_account_id}".format(
                project_id=project_id,
                service_account_id=service_account_id,
            )
        )
        .execute()
    )

    for key in result.get("keys"):
        yield key["name"].split("/")[-1]


def get_service_account_key_metrics(project_id, time_range):
    now = time.time()
    seconds = int(now)
    then = seconds - int(time_range.total_seconds())
    nanos = int((now - seconds) * 10 ** 9)
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": seconds, "nanos": nanos},
            "start_time": {"seconds": then, "nanos": nanos},
        }
    )

    client = monitoring_v3.MetricServiceClient()
    results = client.list_time_series(
        request={
            "name": "projects/{project_id}".format(project_id=project_id),
            "filter": 'metric.type = "iam.googleapis.com/service_account/key/authn_events_count"',
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }
    )

    sa_usage = dict()
    for result in results:
        service_account_id = result.resource.labels["unique_id"]
        key_id = result.metric.labels["key_id"]

        sa_usage.setdefault(service_account_id, {"total_uses": 0, "keys": {}})["keys"][
            key_id
        ] = 0
        for point in result.points:
            sa_usage[service_account_id]["total_uses"] += point.value.int64_value
            sa_usage[service_account_id]["keys"][key_id] += point.value.int64_value

    return sa_usage


def get_sa_key_usage(service_accounts, project_id, time_range):
    sa_usage = get_service_account_key_metrics(project_id, time_range)
    for sa_id, usage in sa_usage.items():
        service_accounts[sa_id]["totalUses"] = usage["total_uses"]
        service_accounts[sa_id]["keys"] |= usage["keys"]

    return service_accounts


def main():
    parser = argparse.ArgumentParser(description="List service account usage.")
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="List service account usage for the specific project",
    )
    group_time_range = parser.add_mutually_exclusive_group()
    group_time_range.add_argument(
        "--hours", type=int, default=0, help="List usage for the last number of hours"
    )
    group_time_range.add_argument(
        "--days", type=int, default=0, help="List usage for the last number of days"
    )
    group_time_range.set_defaults(hours=2)
    args = parser.parse_args()

    service_accounts = get_service_accounts(args.project)
    if not service_accounts:
        return

    time_range = datetime.timedelta(
        **{k: v for k, v in vars(args).items() if k in ["hours", "days"]}
    )

    service_account_usage = get_sa_key_usage(service_accounts, args.project, time_range)

    print(json.dumps(service_account_usage))


if __name__ == "__main__":
    sys.exit(main())
