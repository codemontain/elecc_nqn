import pandas as pd
df = pd.read_csv('Datos_Norte_NQN - departamentos.csv')
print(df.head().to_markdown(index=False))
print(df.info())