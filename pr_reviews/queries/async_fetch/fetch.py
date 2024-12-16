import aiohttp
import asyncio

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_batch(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def batch_fetch_results(urls, batch_size=5):
    results = []
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        batch_results = await fetch_batch(batch)
        results.extend(batch_results)
    return results

# Example usage
# if __name__ == "__main__":
#     urls = [
#         "https://api.github.com",
#         "https://httpbin.org/get",
#         "https://jsonplaceholder.typicode.com/posts/1",
#         "https://jsonplaceholder.typicode.com/posts/2",
#         "https://jsonplaceholder.typicode.com/posts/3",
#         "https://jsonplaceholder.typicode.com/posts/4",
#         "https://jsonplaceholder.typicode.com/posts/5",
#         "https://jsonplaceholder.typicode.com/posts/6"
#     ]
#     results = asyncio.run(main(urls))
#     for result in results:
#         print(result)