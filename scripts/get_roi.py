import os
from datetime import datetime, timedelta
import sys

import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource(
    'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")
dynamo_table = dynamodb.Table("TennisPlayerROI")


def main(name, surface):
    # example
    items = query_items_by_player_surface(
        name, surface)
    for item in items:
        print(item["surfaceTimestamp"], item["roi"])
    print(f"roi: {sum([item['roi'] for item in items])}")
    print(f"count: {len(items)}")


def query_items(player_name, surface, from_date="0000-01-01", to_date="9999-12-31"):
    to_date = decrement_date(to_date)
    response = dynamo_table.query(
        KeyConditionExpression=Key('playerName').eq(player_name) &
        Key('surfaceTimestamp').between(
            f"{surface}#{from_date}", f"{surface}#{to_date}"),
        ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
    )
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = dynamo_table.query(
            KeyConditionExpression=Key('playerName').eq(player_name) &
            Key('surfaceTimestamp').between(
                f"{surface}#{from_date}", f"{surface}#{to_date}"),
            ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        if 'LastEvaluatedKey' in response:
            print("LastEvaluatedKey: {}".format(response['LastEvaluatedKey']))
        data.extend(response['Items'])
    return data


def query_items_by_player_surface(player_name, surface, from_date="0000-01-01", to_date="9999-12-31", count=0):
    to_date = decrement_date(to_date)
    response = dynamo_table.query(
        KeyConditionExpression=Key('playerName').eq(player_name) &
        Key('surfaceTimestamp').between(
            f"{surface}#{from_date}", f"{surface}#{to_date}"),
        ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
    )
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = dynamo_table.query(
            KeyConditionExpression=Key('playerName').eq(player_name) &
            Key('surfaceTimestamp').between(
                f"{surface}#{from_date}", f"{surface}#{to_date}"),
            ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        if 'LastEvaluatedKey' in response:
            print("LastEvaluatedKey: {}".format(response['LastEvaluatedKey']))
        data.extend(response['Items'])
    return data[-count:]


def query_h2h(home, away, from_date="0000-01-01", to_date="9999-12-31"):
    response = dynamo_table.query(
        IndexName='head-to-head',
        KeyConditionExpression=Key('playerName').eq(
            home) & Key('enemy').eq(away),
        FilterExpression=Attr('timestamp').between(from_date, to_date),
        ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
    )
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = dynamo_table.query(
            IndexName='head-to-head',
            KeyConditionExpression=Key('playerName').eq(
                home) & Key('enemy').eq(away),
            FilterExpression=Attr('timestamp').between(from_date, to_date),
            ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        if 'LastEvaluatedKey' in response:
            print("LastEvaluatedKey: {}".format(response['LastEvaluatedKey']))
        data.extend(response['Items'])
    return data


def decrement_date(given_date):
    date_format = '%Y-%m-%d'
    dtObj = datetime.strptime(given_date, date_format)
    past_date = dtObj - timedelta(days=1)
    return past_date.strftime(date_format)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        name = input("name: ")
        surface = input("surface: ")
    else:
        name = sys.argv[1]
        surface = sys.argv[2]
    main(name, surface)
