# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import re
import os
import json
import traceback
from dotenv import load_dotenv

from decimal import Decimal
import json
import boto3
import requests
import time
from scrapy.exceptions import DropItem

# useful for handling different item types with a single interface
from tennis_explorer.sort_csv import sort_csv

from scripts.get_roi import query_items_by_player_surface, query_h2h


class PredictionsPipeline:
    def process_item(self, item, spider):
        return item


class TennisExplorerPipeline:
    def process_item(self, item, spider):
        if item["strong_predict"]:
            try:
                self.place_bet(item)
            except Exception as e:
                print(e)
        return item

    def close_spider(self, spider):
        try:
            print(spider.NEXT_24_HOURS_MATCHES)
            sort_csv(spider.NEXT_24_HOURS_MATCHES, 1, False)
        except Exception as e:
            pass

    def place_bet(self, item):
        betting_api_endpoint = os.environ.get("API_BETTING_ENDPOINT")
        player1 = item["player1_name"]
        player2 = item["player2_name"]
        player1_name = re.sub("\\s[A-Z]+\\.", "",
                              player1).split("-")[0].split(" ")[-1]
        player2_name = re.sub("\\s[A-Z]+\\.", "",
                              player2).split("-")[0].split(" ")[-1]

        try:
            team = ""
            if item["predict"] == 1:
                team = "Team1"

            if item["predict"] == 2:
                team = "Team2"

            if not team:
                return

            data = {
                'username': os.environ.get("PINNACLE_USERNAME"),
                'password': os.environ.get("PINNACLE_PASSWORD"),
                'home': player1_name,
                'away': player2_name,
                'team': team,
                'stake': int(os.environ.get("STAKE")),
            }

            requests.post(url=betting_api_endpoint,
                          json=data, timeout=(12.0, 12.0))

            return item

        except:
            print(traceback.format_exc())
            print(player1_name, player2_name, team)
            return DropItem


class OddsHistoryPipeline:
    def open_spider(self, spider):
        load_dotenv()
        self.dynamodb = boto3.resource(
            'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")

    def process_item(self, item, spider):
        self.put_item(item)
        return item

    def put_item(self, item):
        dynamo_table = self.dynamodb.Table("TennisPlayerROI")
        try:
            for i in range(1, 3):
                set1 = item["set1"]
                set2 = item["set2"]
                set3 = item["set3"] if item["set3"] else ""
                if i == 2:
                    set1 = "".join(reversed(set1))
                    set2 = "".join(reversed(set2))
                    set3 = "".join(reversed(set3))

                params = {
                    "playerName": item[f"player{i}_name"],
                    "timestamp": item["timestamp"],
                    "enemy": item[f"player{3 - i}_name"],
                    "surfaceTimestamp": f"{item['surface']}#{item['timestamp'].split(' ')[0]}",
                    "odds": item[f"player{i}_odds"],
                    "roi": round(item[f"player{i}_odds"] - 1, 2) if int(item["winner"]) == i else -1,
                    "title": item["title"],
                    "surface": item["surface"],
                    "prize": int(item["prize"]),
                    "set1": set1,
                    "set2": set2,
                    "set3": set3,
                }
                ddb_data = json.loads(json.dumps(params), parse_float=Decimal)
                dynamo_table.put_item(Item=ddb_data)
        except Exception:
            print(traceback.format_exc())
