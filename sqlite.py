import sqlite3

connection = sqlite3.connect("student.db")

cursor = connection.cursor()

table_info =""" 
Create table STUDENT(NAME VARCHAR(25), CLASS VARCHAR(25), SECTION VARCHAR(25));
"""

cursor.execute(table_info)

cursor.execute('''Insert Into STUDENT values('Esmoli', 'ml','A')''')
cursor.execute('''Insert Into STUDENT values('Khushi', 'dl','B')''')
cursor.execute('''Insert Into STUDENT values('Jhanvi', 'NLP','c')''')
cursor.execute('''Insert Into STUDENT values('Smriti', 'DL','B')''')
cursor.execute('''Insert Into STUDENT values('Gungun', 'ml','A')''')
cursor.execute('''Insert Into STUDENT values('Tanu', 'NLP','C')''')



print("The inserted records are")
data = cursor.execute('''Select * from STUDENT''')
for row in data:
  print(row)



connection.commit()
connection.close()