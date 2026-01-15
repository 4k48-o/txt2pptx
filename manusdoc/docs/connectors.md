# Overview

> Connect your apps to Manus for AI-powered automation

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

Connectors allow Manus to access and control your other apps directly from your tasks.

**Use cases:**

* Have Manus read and respond to your Gmail messages
* Let Manus schedule meetings in your Google Calendar
* Enable Manus to search and update your Notion databases

## Popular Connectors

<CardGroup cols={3}>
  <Card title="Gmail" href="/connectors/gmail">
    Connect your Gmail account to manage emails with AI assistance
  </Card>

  <Card title="Google Calendar" href="/connectors/google-calendar">
    Integrate with Google Calendar for intelligent scheduling
  </Card>

  <Card title="Notion" href="/connectors/notion">
    Connect your Notion workspace for AI-powered knowledge management
  </Card>
</CardGroup>

## Setup

You can set up your integrations from [manus.im](https://manus.im) using secure OAuth authentication. Each connector uses industry-standard OAuth protocols to ensure your data remains secure and private.

## All Available Connectors

<Card title="Supported Connectors">
  The table below lists all supported connectors. We're constantly adding more. Click a connector's name for its documentation, or click its UUID to copy it.
</Card>

<ConnectorTable />

To use a connector, copy its UUID and include it in the `connectors` array of your API request. For an example, see the [Create Task](/api-reference/create-task) page.


---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://open.manus.ai/docs/llms.txt