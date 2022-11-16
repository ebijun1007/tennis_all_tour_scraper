import os
import boto3

dynamodb = boto3.resource(
    'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")
dynamo_table = dynamodb.Table("TennisPlayerROI")


def create_table():
    table = dynamodb.create_table(
        TableName='TennisPlayerROI',
        KeySchema=[
            {
                'AttributeName': 'playerName',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'surfaceTimestamp',
                'KeyType': 'RANGE'
            }
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'head-to-head',
                'KeySchema': [
                    {
                        'AttributeName': 'playerName',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'enemy',
                        'KeyType': 'RANGE'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL',
                }
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'playerName',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'surfaceTimestamp',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'enemy',
                'AttributeType': 'S'
            },
        ],
        # オンデマンドにする場合
        BillingMode='PAY_PER_REQUEST'
    )
    return table


if __name__ == '__main__':
    print('Create table...')
    table = create_table()

    table.wait_until_exists()
    print('Created!')
    print('Table status:', table.table_status)
    print('Item count:', table.item_count)
