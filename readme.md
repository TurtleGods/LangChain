# 使用步驟
1. 在根目錄建立一個.env file，裡面寫入 <br>OPENAI_API_KEY="你自己的OPENAI_API_KEY" <br>
JIRA_TOKEN="你自己的JIRA_TOKEN"<br>
JIRA_URL=https://mayohumancapital.atlassian.net<br>
JIRA_EMAIL="你自己的JIRA MAYO EMAIL"<br>
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/langchain_db<br>
2. 安裝mkcert，使用Mkcert建立一個本機的SSL<br>
3. 根目錄下面放置一個SSL 的folder，放入你的localhost.pem跟localhost-key.pem<br>
4. 安裝[docker desktop](https://www.docker.com/)
# 執行
根目錄的terminal之中，下指令docker compose up<br>
如果不想要它佔據你的termial 的話，下docker compose up -d<br>
關閉的話，則下指令docker compose down<br>
**注意**
如果compose down的話，Chromadb要重新建立<br>
但是postgreSQL是用Volume建立，不用重新拉資料
# SQL
建議使用[DBeaver](https://dbeaver.io/)<br>
連線localhost:5432<br>
database:langchain_db<br>
Username:postgres<br>
password:postgres<br>
# API
拿取Jira，先建立資料庫跟Chroma:<br>
[put]
https://localhost:8000/jira/

問問題:<br>
[post]
https://localhost:8000/openAI/ask <br>
body:{"question":"{你的問題}"}<br>

