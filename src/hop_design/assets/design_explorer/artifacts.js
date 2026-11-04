// Cache immutable artifact URLs, not mutable selections or molecular records.
export function artifactLoader(fetcher=fetch, entries=6, byteLimit=8*1024*1024) {
  const items=new Map(); let bytes=0, generation=0;
  return {
    async text(url) {
      if(items.has(url)) {
        const item=items.get(url);items.delete(url);items.set(url,item);return item.text;
      }
      const admittedGeneration=generation, response=await fetcher(url);
      if(!response.ok) throw Error('This inspection artifact expired or is unavailable. Reopen the saved view to regenerate its preview.');
      const text=await response.text(), size=new TextEncoder().encode(text).length;
      if(admittedGeneration===generation && size<=byteLimit) {
        bytes-=items.get(url)?.size ?? 0;
        items.delete(url);
        items.set(url,{text,size});bytes+=size;
        while(items.size>entries || bytes>byteLimit) {
          const key=items.keys().next().value;bytes-=items.get(key).size;items.delete(key);
        }
      }
      return text;
    },
    clear(){generation++;items.clear();bytes=0;},
  };
}
