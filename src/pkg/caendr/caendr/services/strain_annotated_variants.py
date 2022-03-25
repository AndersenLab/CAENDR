import re


def verify_interval_query(query):
  query_regex = "^(I|II|III|IV|V|X|MtDNA):[0-9,]+-[0-9,]+$"
  match = re.search(query_regex, query) 
  return True if match else False


def verify_position_query(query):
  query_regex = "^(I|II|III|IV|V|X|MtDNA):[0-9,]+$"
  match = re.search(query_regex, query) 
  return True if match else False