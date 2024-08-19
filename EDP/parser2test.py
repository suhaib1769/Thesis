from parser_2 import Parser2
import pandas as pd

xml_file_path = '/Users/suhaibbasir/Documents/CS/MSc/Thesis/Thesis/EDP/output_solr33.xml'

# data = Parser2.XLMtoDict(xml_file_path)
data = Parser2.XLMtoString(xml_file_path)

# print first and last 5 records
print(data[0])
# print(data[-5:])
