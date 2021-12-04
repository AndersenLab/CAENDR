import re


def verify_interval_query(q):
  query_regex = "^(I|II|III|IV|V|X|MtDNA):[0-9,]+-[0-9,]+$"
  match = re.search(query_regex, q) 
  return True if match else False


def verify_position_query(q):
  query_regex = "^(I|II|III|IV|V|X|MtDNA):[0-9,]+$"
  match = re.search(query_regex, q) 
  return True if match else False