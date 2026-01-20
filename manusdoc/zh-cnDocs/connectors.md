# 概览

> 把你的应用连接到 Manus，实现 AI 驱动的自动化

export const ConnectorTable = () => {
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [copiedUuid, setCopiedUuid] = React.useState(null);
  const connectorPages = {
    'Gmail': '/connectors/gmail',
    'Google Calendar': '/connectors/google-calendar',
    'Notion': '/connectors/notion'
  };
  React.useEffect(() => {
    const fetchConnectors = async () => {
      try {
        const response = await fetch('https://api.manus.im/connectors.v1.ConnectorsPublicService/PublicListConnectors', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            offset: 0,
            limit: 100
          })
        });
        const result = await response.json();
        setData(result);
      } catch (error) {
        setData({
          error: error.message
        });
      } finally {
        setLoading(false);
      }
    };
    fetchConnectors();
  }, []);
  if (loading) return null;
  if (!data || !data.connectors) {
    return null;
  }
  const copyToClipboard = async text => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedUuid(text);
      setTimeout(() => setCopiedUuid(null), 2000);
    } catch (err) {
      console.error('Failed to copy: ', err);
    }
  };
  return <div className="w-full">
      <div className="grid grid-cols-2 gap-4 border-b border-gray-200 dark:border-gray-700 pb-2 mb-3">
        <div className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Connector Name
        </div>
        <div className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          UUID
        </div>
      </div>
      <div className="space-y-2">
        {data.connectors.map(connector => {
    const hasDocPage = connectorPages[connector.name];
    return <div key={connector.uid} className="grid grid-cols-2 gap-4 border-b border-gray-200 dark:border-gray-700 pb-2">
              <div className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-white">
                {hasDocPage ? <a href={hasDocPage} className="text-blue-600 dark:text-blue-400 hover:underline">
                    {connector.name}
                  </a> : connector.name}
              </div>
              <button type="button" className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 font-mono cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 transition-colors relative group text-left" onClick={() => copyToClipboard(connector.uid)} onKeyDown={e => e.key === 'Enter' && copyToClipboard(connector.uid)}>
                <span className="underline decoration-dotted decoration-1 underline-offset-2">
                  {connector.uid}
                </span>
                {}
                <div className="absolute -top-10 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap pointer-events-none z-10">
                  Click to copy UUID
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
                </div>
                {}
                {copiedUuid === connector.uid && <div className="absolute -top-10 left-1/2 transform -translate-x-1/2 bg-green-600 text-white text-xs px-2 py-1 rounded opacity-100 transition-opacity duration-200 whitespace-nowrap pointer-events-none z-10">
                    Copied! ✓
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-green-600"></div>
                  </div>}
              </button>
            </div>;
  })}
      </div>
    </div>;
};

Connectors 允许 Manus 直接访问并控制你的其他应用，从而在任务里完成跨系统的自动化操作。

**使用场景：**

* 让 Manus 读取并回复你的 Gmail 邮件
* 让 Manus 在 Google Calendar 中安排会议
* 让 Manus 搜索并更新你的 Notion 数据库

## 热门 Connectors

<CardGroup cols={3}>
  <Card title="Gmail" href="/connectors/gmail">
    连接你的 Gmail 账号，用 AI 协助管理邮件
  </Card>

  <Card title="Google Calendar" href="/connectors/google-calendar">
    与 Google Calendar 集成，实现智能日程安排
  </Card>

  <Card title="Notion" href="/connectors/notion">
    连接你的 Notion 工作区，进行 AI 驱动的知识管理
  </Card>
</CardGroup>

## 配置

你可以在 [manus.im](https://manus.im) 中通过安全的 OAuth 认证来配置这些集成。每个 connector 都采用业界标准的 OAuth 协议，以确保你的数据安全与隐私。

## 所有可用 Connectors

<Card title="支持的 Connectors">
  下表列出了所有支持的 connectors。我们会持续新增更多。点击 connector 名称可查看其文档；点击 UUID 可复制。
</Card>

<ConnectorTable />

使用某个 connector 时，复制其 UUID，并将其放入 API 请求中的 `connectors` 数组即可。示例可参考 [Create Task](/api-reference/create-task) 页面。


---

> 若要查看本套文档的导航与其他页面，请访问 llms.txt：`https://open.manus.ai/docs/llms.txt`

