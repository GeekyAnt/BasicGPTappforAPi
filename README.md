# BasicGPTappforAPi
Super basic python based chat app for working with ChatGPT API. Records output to PostgreSQL server for recall

To work it also requires an additional .py file in the same folder containing



config = {
    "openai_key": "[API-KEY-HERE]",
    "database": {
        "host": "192.168.1.130",
        "port": "5432",
        "dbname": "[DBnameHere]",
        "user": "[UserNameHere]",
        "password": "[PasswordHere]"
    }
}
