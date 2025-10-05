
#%%
from modules.bedrock import call_bedrock_api
from modules.crawling import get_contents




#%%



output = get_contents('https://www.smentertainment.com/newsroom/%ec%bb%b4%eb%b0%b1-%ec%97%91%ec%86%8c-%ec%88%98%ed%98%b8-%eb%a9%9c%eb%a1%a0-%eb%9d%bc%ec%9d%b4%eb%b8%8c-%ea%b3%b5%ec%97%b0-%ec%84%b1%ec%88%98%eb%8f%99-%eb%b2%84%ec%8a%a4/')

# %%

output
# %%


prompt = '아래 자료를 보고 적절한 기사를 작성하시오\n\n\n\n'

response = call_bedrock_api(
    prompt,
    output['html'] + '\n\n\n\n'
)


# %%
result = response['content'][0]['text']


print(result)




# %%
