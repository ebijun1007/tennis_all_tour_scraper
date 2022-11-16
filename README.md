# tennis_major_tour_scraper

Crawl results of major tennis competitions from [tennisexplorer.com](https://www.tennisexplorer.com/)

## How to run crawler

### On local machine

```
$ pip install -r requirements.txt
$ scrapy crawl results
```

### On docker container

```
$ docekr build . -t ${IMAGE_NAME}`
$ docker run -v #{PWD}:/app --rm ${IMAGE_NAME} python scrapy crawl results
```

### Merge CSV files

The results are exported to `data` folder daily.
You can merge them to one file by below command.

```
$ python join_csv.py
```
# tennis_all_tour_scraper
# tennis_all_tour_scraper
