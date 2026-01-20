# 快速开始

> 生成一个 API Key，并完成你的第一次调用。

## 创建你的 API Key

<Card title="获取你的 API Key" horizontal arrow icon="key" href="http://manus.im/app?show_settings=integrations&app_name=api">
  打开 API Integration（API 集成）设置页面，生成一个新的 Key。
</Card>

<Warning>
  请妥善保管你的 API Key，切勿公开分享。每个 Key 都拥有对你的 Manus 账号的完整访问权限。
</Warning>

## 发起你的第一次 API 调用

<Tabs>
  <Tab title="cURL">
    ```shell lines theme={null}
    curl --request POST \
      --url 'https://api.manus.ai/v1/tasks' \
      --header 'accept: application/json' \
      --header 'content-type: application/json' \
      --header "API_KEY: $MANUS_API_KEY" \
      --data '{
        "prompt": "hello"
      }'
    ```
  </Tab>

  <Tab title="Python">
    ```python lines theme={null}
    import requests

    url = "https://api.manus.ai/v1/tasks"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "API_KEY": f"{MANUS_API_KEY}"
    }
    data = {
        "prompt": "hello"
    }

    response = requests.post(url, json=data, headers=headers)
    print(response.json())
    ```
  </Tab>

  <Tab title="TypeScript">
    ```typescript lines theme={null}
    const response = await fetch('https://api.manus.ai/v1/tasks', {
      method: 'POST',
      headers: {
        'accept': 'application/json',
        'content-type': 'application/json',
        'API_KEY': `${process.env.MANUS_API_KEY}`
      },
      body: JSON.stringify({
        prompt: 'hello'
      })
    });

    const data = await response.json();
    console.log(data);
    ```
  </Tab>
</Tabs>

## 下一步

现在你已经完成了第一次 API 调用，下面是一些继续了解 Manus API 的方向：

<Card title="用 3 行代码从 OpenAI 切换过来" horizontal icon="rocket" href="/openai-compatibility/index">
  了解我们的 Responses API：它允许你仅用 3 行代码就从 OpenAI 切换到 Manus API。
</Card>

<CardGroup>
  <Card title="API 参考" icon="code" href="/api-reference/create-task">
    查看完整的 API 文档与每个端点的详细规范。
  </Card>

  <Card title="Webhooks" icon="bell" href="/webhooks/introduction">
    获取任务生命周期事件的实时通知。
  </Card>
</CardGroup>


---

> 若要查看本套文档的导航与其他页面，请访问 llms.txt：`https://open.manus.ai/docs/llms.txt`

