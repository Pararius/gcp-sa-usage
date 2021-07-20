#!/usr/bin/env python
import argparse
import datetime
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
        .list(name="projects/" + project_id)
        .execute()
    )

    return result.get("accounts")


def get_service_account_usage(project_id, time_range):
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

    sa_uses = dict()
    for result in results:
        service_account_id = result.resource.labels["unique_id"]
        key_id = result.metric.labels["key_id"]

        sa_uses.setdefault(service_account_id, {"total_uses": 0, "keys": {}})["keys"][
            key_id
        ] = 0
        for point in result.points:
            sa_uses[service_account_id]["total_uses"] += point.value.int64_value
            sa_uses[service_account_id]["keys"][key_id] += point.value.int64_value

    return sa_uses


def list_sa_key_uses(service_accounts, project_id, time_range):
    if not service_accounts:
        return

    sa_uses = get_service_account_usage(project_id, time_range)
    for sa in service_accounts:
        account_usage = sa_uses.get(sa["uniqueId"], {})
        print(
            "{sa}: {sa_uses} ({project})".format(
                project=project_id,
                sa=sa["email"],
                sa_uses=account_usage.get("total_uses", 0),
            )
        )

        for key, key_uses in account_usage.get("keys", {}).items():
            print("  key({key}): {uses}".format(key=key, uses=key_uses))

        print()


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

    time_range = datetime.timedelta(
        **{k: v for k, v in vars(args).items() if k in ["hours", "days"]}
    )

    service_account_usage = get_service_accounts(args.project)
    list_sa_key_uses(service_account_usage, args.project, time_range)


if __name__ == "__main__":
    sys.exit(main())
