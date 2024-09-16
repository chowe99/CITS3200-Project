


import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt

#names will be change once database is created
mydb = mysql.connector.connect(
  host="localhost",
  user="username",
  password="password",
  database="database"
)

mycursor = mydb.cursor()

query = "SELECT p, q FROM x"
mycursor.execute(query)
myresult = mycursor.fetchall()

#create dataframe with pandas and plot with pyplot
df = pd.DataFrame(myresult, columns=['p', 'q'])
df.plot(kind='scatter', x='p', y='q')
plt.xlabel("p'")
plt.ylabel('q')
plt.show()



  