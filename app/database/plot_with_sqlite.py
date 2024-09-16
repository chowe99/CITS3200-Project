import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

conn = sqlite3.connect('test.db')
query = "SELECT axial_strain, shear_induced_PWP, p, q FROM CSL_1_U"
df = pd.read_sql_query(query, conn)
conn.close()

#df.plot(kind='scatter', x='axial_strain', y='shear_induced_PWP')

#plt.xlabel('Axial strain')
#plt.ylabel('Shear induced PWP')
#plt.show()

df.plot(kind='scatter', x='p', y='q')
plt.xlabel("p'")
plt.ylabel('q')
plt.show()