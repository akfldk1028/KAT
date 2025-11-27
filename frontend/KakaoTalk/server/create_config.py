
content = """export default {
  auth: {
    key: 'kanana-dualguard-secret-key'
  },
  db: {
    url: 'sqlite://../../../backend/kanana_dualguard.db'
  }
};"""

with open('src/config.ts', 'w', encoding='utf-8') as f:
    f.write(content)
print("config.ts created successfully")
