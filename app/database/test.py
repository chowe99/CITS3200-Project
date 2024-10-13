from cleaning_script import data_extractor

print(data_extractor('test.csv', '03 - Shearing'))


import pandas as pd
from sqlalchemy import create_engine


mydb = mysql.connector.connect(
  host="localhost",
  user="yourusername",
  password="yourpassword",
  database="mydatabase"
)

df = data_extractor('test.csv', '03 - Shearing')


engine = create_engine("mysql+mysqlconnector://root:new_password@localhost/mydatabase")
df.to_sql('table_name', con=engine, if_exists='replace', index=False)

