package main

import (
	"bufio"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func Scrape(url string) {
	baseUrl := "http://www.tennisexplorer.com/"
	res := get(url)
	// defer res.Body.Close()

	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		log.Fatal(err)
	}

	doc.Find("#center > div:nth-child(3) > table > thead a").Each(func(i int, s *goquery.Selection) {
		player_path, ok := s.Attr("href")
		if ok {
			fmt.Printf("Review %d: %s\n", i, player_path)
			calc_roi(baseUrl + player_path)
		}
	})
}

func calc_roi(url string) {
	res := get(url)
	// defer res.Body.Close()

	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		log.Fatal(err)
	}

	balance := 1.0

	doc.Find("#matches-2022-1-data tbody tr").EachWithBreak(func(i int, s *goquery.Selection) bool {
		if strings.Contains(s.Find("span").First().Text(), "Futures") {
			return false
		}
		if s.HasClass("head") {
			return true
		}
		odds, err := strconv.ParseFloat(s.Find("td.course").First().Text(), 64)
		if err != nil {
			return true
		}

		balance -= 1
		win := s.Find("a").First().HasClass("notU")
		if win {
			balance += odds
		}

		return true

	})
	fmt.Printf("%f\n", balance)

}

func get(url string) (res *http.Response) {
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36")

	client := new(http.Client)
	res, err := client.Do(req)
	if err != nil {
		log.Fatal(err)
	}
	return
}

func main() {
	for {
		fmt.Print("URL? ")
		// Scannerを使って一行読み
		scanner := bufio.NewScanner(os.Stdin)
		scanner.Scan()
		// url := os.Args[1]
		url := scanner.Text()
		if !strings.Contains(url, "https") {
			continue
		}
		Scrape(url)
	}
}
