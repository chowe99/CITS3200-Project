from cleaning_script import data_extractor
import sqlite3

df1 = data_extractor('CSL_1_U.xlsx', '03 - Shearing')
df2 = data_extractor('CSL_2_U.xlsx', '03 - Shearing')
df3 = data_extractor('CSL_3_D.xlsx', '03 - Shearing')

conn = sqlite3.connect('test.db')

df1.to_sql('CSL_1_U', conn, if_exists='replace', index=False)
df2.to_sql('CSL_2_U', conn, if_exists='replace', index=False)
df2.to_sql('CSL_3_D', conn, if_exists='replace', index=False)

conn.close()
