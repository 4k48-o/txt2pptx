# Similarweb

> Access website traffic and digital market intelligence data

export const CodePrompt = ({children}) => {
  const [isCopied, setIsCopied] = useState(false);
  const textContent = useMemo(() => {
    const extractText = (children, depth = 0) => {
      const maxDepth = 10;
      if (depth > maxDepth) return '';
      if (children == null) return '';
      if (typeof children === 'string' || typeof children === 'number') {
        return String(children);
      }
      if (Array.isArray(children)) {
        return children.map(child => extractText(child, depth + 1)).join('');
      }
      if (typeof children === 'object' && children.props) {
        return extractText(children.props.children, depth + 1);
      }
      return '';
    };
    return extractText(children);
  }, [children]);
  const handleAskManus = useCallback(() => {
    const url = new URL('https://manus.im');
    if (textContent) {
      url.searchParams.set('q', textContent);
      url.searchParams.set('submit', '1');
    }
    window.open(url.toString(), '_blank');
  }, [textContent]);
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(textContent);
      setIsCopied(true);
      setTimeout(() => {
        setIsCopied(false);
      }, 2000);
    } catch (err) {
      const textArea = document.createElement('textarea');
      textArea.value = textContent;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setIsCopied(true);
        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      } catch (fallbackErr) {
        console.error(fallbackErr);
      }
      document.body.removeChild(textArea);
    }
  }, [textContent]);
  return <div className="code-block mt-5 mb-8 not-prose rounded-2xl relative group text-gray-950 dark:text-gray-50 codeblock-light border border-gray-950/10 dark:border-white/10 dark:twoslash-dark bg-transparent dark:bg-transparent">
      <div className="absolute top-3 right-4 flex items-center gap-1.5">
        <div className="z-10 relative">
          <button onClick={handleCopy} className="h-[26px] w-[26px] flex items-center justify-center rounded-md backdrop-blur peer group/copy-button " data-testid="copy-code-button" aria-label="Copy the contents from the code block">
            {isCopied ? <svg width="16" height="11" viewBox="0 0 16 11" fill="none" xmlns="http://www.w3.org/2000/svg" class="fill-primary dark:fill-primary-light">
                <path d="M14.7813 1.21873C15.0751 1.51248 15.0751 1.98748 14.7813 2.2781L6.53135 10.5312C6.2376 10.825 5.7626 10.825 5.47197 10.5312L1.21885 6.28123C0.925098 5.98748 0.925098 5.51248 1.21885 5.22185C1.5126 4.93123 1.9876 4.9281 2.27822 5.22185L5.99697 8.9406L13.7188 1.21873C14.0126 0.924976 14.4876 0.924976 14.7782 1.21873H14.7813Z"></path>
              </svg> : <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-400 group-hover/copy-button:text-gray-500 dark:text-white/40 dark:group-hover/copy-button:text-white/60">
                <path d="M14.25 5.25H7.25C6.14543 5.25 5.25 6.14543 5.25 7.25V14.25C5.25 15.3546 6.14543 16.25 7.25 16.25H14.25C15.3546 16.25 16.25 15.3546 16.25 14.25V7.25C16.25 6.14543 15.3546 5.25 14.25 5.25Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"></path>
                <path d="M2.80103 11.998L1.77203 5.07397C1.61003 3.98097 2.36403 2.96397 3.45603 2.80197L10.38 1.77297C11.313 1.63397 12.19 2.16297 12.528 3.00097" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>}
          </button>
          <div aria-hidden="true" className="absolute top-11 left-1/2 transform whitespace-nowrap -translate-x-1/2 -translate-y-1/2 peer-hover:opacity-100 opacity-0 text-white rounded-lg px-1.5 py-0.5 text-xs bg-primary-dark">
            {isCopied ? 'Copied' : 'Copy'}
          </div>
        </div>
        <div className="z-10 relative">
          <button onClick={handleAskManus} className="h-[26px] w-[26px] flex items-center justify-center rounded-md backdrop-blur peer group/ask-manus " id="ask-ai-code-block-button" aria-label="Ask Manus">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" className="w-4 h-4 text-gray-400 group-hover/ask-manus:text-gray-500 dark:text-white/40 dark:group-hover/ask-manus:text-white/60">
              <path d="M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z" />
              <path d="M12 8v6" />
              <path d="M9 11h6" />
            </svg>
          </button>
          <div aria-hidden="true" className="absolute top-11 left-1/2 transform whitespace-nowrap -translate-x-1/2 -translate-y-1/2 peer-hover:opacity-100 opacity-0 text-white rounded-lg px-1.5 py-0.5 text-xs bg-primary-dark">
            Ask Manus
          </div>
        </div>
      </div>

      <div className="w-0 min-w-full max-w-full py-3.5 px-4 h-full dark:bg-codeblock relative text-sm leading-6 children:!my-0 children:!shadow-none children:!bg-transparent transition-[height] duration-300 ease-in-out code-block-background [&_*]:ring-0 [&_*]:outline-0 [&_*]:focus:ring-0 [&_*]:focus:outline-0 [&_pre>code]:pr-[3rem] [&_pre>code>span.line-highlight]:min-w-[calc(100%+3rem)] [&_pre>code>span.line-diff]:min-w-[calc(100%+3rem)] rounded-2xl bg-white overflow-x-auto scrollbar-thin scrollbar-thumb-rounded scrollbar-thumb-black/15 hover:scrollbar-thumb-black/20 active:scrollbar-thumb-black/20 dark:scrollbar-thumb-white/20 dark:hover:scrollbar-thumb-white/25 dark:active:scrollbar-thumb-white/25" style={{
    fontVariantLigatures: 'none',
    height: 'auto',
    backgroundColor: 'rgb(255, 255, 255)'
  }}>
        <div className="font-mono whitespace-pre leading-6">{children}</div>
      </div>
    </div>;
};

## Overview

Manus integrates Similarweb data access directly into your workflow. Without additional configuration or API management, you can access comprehensive website analytics and digital market intelligence simply through natural language prompts.

## How to Use

Simply mention the data you need in your prompt. Manus will automatically use Similarweb to fetch the information when related info is detected.

Traffic Analysis

<CodePrompt>
  Show me monthly visits, bounce rate, and pages per visit for example.com over the last 6 months. Include month-over-month changes.
</CodePrompt>

Marketing Channels

<CodePrompt>
  Break down the marketing channel mix for example.com. What percentage comes from direct, organic search, paid, social, referral, and display?
</CodePrompt>

Geographic Analysis

<CodePrompt>
  Show me the top 10 countries by traffic share for example.com in 2025 Q4. I need to understand their geographic footprint.
</CodePrompt>

## Available Endpoints

The table below lists all supported endpoints. Click any endpoint name to view detailed API documentation and parameters:

### Endpoint Overview

<table>
  <thead>
    <tr>
      <th align="left" width="5%">Type</th>
      <th align="left" width="35%">Endpoint</th>
      <th align="left" width="12%">Unit Cost (Credits)</th>
      <th align="left" width="48%">Description</th>
    </tr>
  </thead>

  <tbody>
    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/unique-visitors">Get Unique Visit</a></td>
      <td>8</td>
      <td>Total number of unique visitors to a domain within a specific timeframe</td>
    </tr>

    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/global-rank">Get Global Rank (Desktop+Mobile Web)</a></td>
      <td>8</td>
      <td>Website's ranking compared to all websites globally</td>
    </tr>

    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/visits">Get Total Visits (Desktop+Mobile Web)</a></td>
      <td>8</td>
      <td>Total number of visits to the website</td>
    </tr>

    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/bounce-rate">Get Bounce Rate (Desktop+Mobile Web)</a></td>
      <td>8</td>
      <td>Percentage of visitors who leave after viewing one page</td>
    </tr>

    <tr>
      <td>B</td>
      <td><a href="https://developers.similarweb.com/reference/geography-total">Get Total Traffic by Country (Desktop+Mobile Web)</a></td>
      <td>56</td>
      <td>Geographic distribution of website traffic</td>
    </tr>

    <tr>
      <td>B</td>
      <td><a href="https://developers.similarweb.com/reference/traffic-sources-overview">Get Traffic Sources by Marketing Channel (Desktop)</a></td>
      <td>56</td>
      <td>Breakdown of desktop traffic channels</td>
    </tr>

    <tr>
      <td>B</td>
      <td><a href="https://developers.similarweb.com/reference/traffic-sources-overview-mobile-web">Get Traffic Sources by Marketing Channel (Mobile)</a></td>
      <td>56</td>
      <td>Breakdown of mobile traffic channels</td>
    </tr>
  </tbody>
</table>

### Data Details

<table>
  <thead>
    <tr>
      <th align="left" width="5%">Type</th>
      <th align="left" width="35%">Endpoint</th>
      <th align="left" width="10%">Regional Granularity</th>
      <th align="left" width="50%">Accessible Information</th>
    </tr>
  </thead>

  <tbody>
    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/unique-visitors">Get Unique Visit</a></td>
      <td>Worldwide</td>
      <td>Share of desktop-only UV; share of mobile web-only UV; share of UV across both mobile web and desktop</td>
    </tr>

    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/global-rank">Get Global Rank (Desktop+Mobile Web)</a></td>
      <td>Worldwide</td>
      <td>Monthly Global Rank</td>
    </tr>

    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/visits">Get Total Visits (Desktop+Mobile Web)</a></td>
      <td>Worldwide</td>
      <td>Total visits to the website across desktop and web mobile</td>
    </tr>

    <tr>
      <td>A</td>
      <td><a href="https://developers.similarweb.com/reference/bounce-rate">Get Bounce Rate (Desktop+Mobile Web)</a></td>
      <td>Worldwide</td>
      <td>Monthly Bounce Rate</td>
    </tr>

    <tr>
      <td>B</td>
      <td><a href="https://developers.similarweb.com/reference/geography-total">Get Total Traffic by Country (Desktop+Mobile Web)</a></td>
      <td>By Country</td>
      <td>Country Name, Country Ranking by share, Share of traffic by country, Total visits by country, Pages per visit by country, Average time by country, Bounce rate by country</td>
    </tr>

    <tr>
      <td>B</td>
      <td><a href="https://developers.similarweb.com/reference/traffic-sources-overview">Get Traffic Sources by Marketing Channel (Desktop)</a></td>
      <td>Worldwide</td>
      <td>Estimated organic and paid desktop visits by channel (Organic Search, Paid Search, Direct, Display Ads, Email, Referrals and Social)</td>
    </tr>

    <tr>
      <td>B</td>
      <td><a href="https://developers.similarweb.com/reference/traffic-sources-overview-mobile-web">Get Traffic Sources by Marketing Channel (Mobile)</a></td>
      <td>Worldwide</td>
      <td>Estimated organic and paid mobile visits by channel (Organic Search, Paid Search, Direct, Display Ads, Email, Referrals and Social)</td>
    </tr>
  </tbody>
</table>

## Price Model

This data integration follows Similarweb's multiplier-based pricing model, where costs are calculated by multiplying multiple factors. [Learn more about pricing →](https://developers.similarweb.com/docs/data-credits-unpublished-whats-new-in-v40)

See the table below for detailed pricing factors:

### Pricing Factors

| Factor          | Description                                                                       | Multiplier         |
| --------------- | --------------------------------------------------------------------------------- | ------------------ |
| **Domains**     | Number of unique domains requested                                                | 1x per domain      |
| **Granularity** | Data resolution<br />*Monthly data only*                                          | 1x                 |
| **Countries**   | Number of countries queried<br />*Global = 1x, specific countries might add cost* | 1x per country     |
| **Time Span**   | Historical data range<br />*Max: 12 months*                                       | 1x per month       |
| **Unit Cost**   | Base cost varies by endpoint category                                             | Varies by endpoint |

<Info>
  **Important Notes:**

  * Only **monthly granularity** data is provided
  * Maximum **12 months** of historical data available
  * **Type A** endpoints: Worldwide data only
</Info>

<Note>
  Manus automatically optimizes queries to minimize costs while delivering accurate results. Session Credits Usage is tracked in your dashboard.
</Note>

### Example Calculations

<Tip>
  **Cost** = **Domains** x **Granularity** × **Countries** × **Time Span** x **Unit Cost**
</Tip>

<table>
  <thead>
    <tr>
      <th align="left" width="15%">Endpoint</th>
      <th align="left" width="40%">Prompt</th>
      <th align="left" width="30%">Cost Calculation</th>
      <th align="left" width="15%">Total</th>
    </tr>
  </thead>

  <tbody>
    <tr>
      <td><strong>Unique Visit</strong></td>
      <td>Show me unique visitors change for <code>example.com</code> over the last year</td>
      <td>1 Domain × 1 Country × 12 Months × 8 Unit Cost</td>
      <td><strong>96 Credits</strong></td>
    </tr>

    <tr>
      <td><strong>Geography</strong></td>
      <td>Get traffic breakdown by country for <code>example.com</code> in the past month, and return only the top 5 countries with the highest traffic</td>
      <td>1 Domain × 5 Countries × 1 Month × 56 Unit Cost</td>
      <td><strong>280 Credits</strong></td>
    </tr>

    <tr>
      <td><strong>Market Channel</strong></td>
      <td>Compare the organic search traffic on mobile web for <code>example1.com</code> and <code>example2.com</code> in the past 3 months</td>
      <td>2 Domain × 1 Country × 3 Months × 56 Unit Cost</td>
      <td><strong>336 Credits</strong></td>
    </tr>
  </tbody>
</table>

<Note>
  The above calculations reflect Data API costs only. Total session credits include additional charges for AI processing, computation, and other features used during the session.
</Note>

<Warning>
  Data accuracy is determined by Similarweb's statistical scope and algorithms. Estimates may vary by website. Always verify critical data with multiple sources.
</Warning>

## Reference

* [Similarweb Developer Documentation](https://developers.similarweb.com/docs/similarweb-web-traffic-api)
* [Similarweb Data Credits System](https://developers.similarweb.com/docs/data-credits-unpublished-whats-new-in-v40)
* [Data Accuracy and Methodology](https://support.similarweb.com/hc/en-us/articles/360002219177-Similarweb-s-Data-Accuracy)

***

Need help with Similarweb data? Ask Manus in natural language and it will handle the technical details for you.


---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://open.manus.ai/docs/llms.txt