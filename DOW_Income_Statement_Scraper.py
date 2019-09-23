from urllib.request import urlopen as uReq
from bs4 import BeautifulSoup as soup
import csv

import lxml
from lxml import html
import requests
import numpy as np
import pandas as pd

dow_url = 'https://ca.finance.yahoo.com/quote/%5EDJI/components?p=%5EDJI'

# opening up connection, grabbing the page
uClient = uReq(dow_url)
page_html = uClient.read()
uClient.close()

# html parsing
page_soup = soup(page_html, "html.parser")

# grab the 30 companies of the DOW 
companies = page_soup.findAll('a', {'class':'C($c-fuji-blue-1-b) Cur(p) Td(n) Fw(500)'})

# Create lists of URL's for Income Statements, Balance Sheets, and Cash Flows

# Income Statement links
fin_links = []
for i in companies:
	fin_links.append('https://ca.finance.yahoo.com/quote/' + i.attrs['title'] + '/financials?p=' + i.attrs['title'])


def scrape_income(inc_url):
	page = requests.get(inc_url)
	tree = html.fromstring(page.content)
	table = tree.xpath("//table")
	tstring = lxml.etree.tostring(table[0], method = 'html')

	df = pd.read_html(tstring)[0]
	df = df.set_index(0) # Set the index to the first column: 'Period Ending'.
	df = df.transpose() # Transpose the DataFrame, so that our header contains the account names
	df = df.replace('-', '0') # Remove the '-' values that can't be converted to numeric.
	df = df.drop(columns = ['Operating Expenses', 'Income from Continuing Operations', "Non-recurring Events",'Net Income'])

	df[df.columns[0]] = pd.to_datetime(df[df.columns[0]])
	cols = list(df.columns)
	cols[0] = 'Date'
	df = df.set_axis(cols, axis='columns', inplace=False)  # Change column names.

	numeric_columns = list(df.columns)[1::] # Take all columns, except the first (which is the 'Period Date' column)
	df[numeric_columns] = df[numeric_columns].astype(np.float64) # Convert all columns to float64

	uClient = uReq(inc_url)
	page_html = uClient.read()
	uClient.close()
	page_soup = soup(page_html, "html.parser")

	df.insert(0, "Company", [page_soup.find('h1').get_text()] + ['']*(len(df)-1), True)

	return df


def compile_income(url_list):
	all_df_list = []
	for i in url_list:
		all_df_list.append(scrape_income(i)) # Combine all dataframes into one.
	appended_df = pd.concat(all_df_list)
	writer = pd.ExcelWriter("AllIncomeStatements.xlsx")
	appended_df.to_excel(writer)
	writer.save()

compile_income(fin_links)