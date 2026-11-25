
def build_context(hits, max_chars=4000):
    """A：把證據組成有來源標籤的context；回傳text與實際放進去的sources。"""
    parts, sources = [], []

    # TODO A：依序處理hits裡的每一筆
    # 1. 標籤依序是[來源1]、[來源2]…；每段寫成「標籤 來源／chunk_id」，換行後接完整原文。
    # 2. 段與段之間空一行（"\n\n"）；加入這段後總長度會超過max_chars就停止，不切半。
    # 3. 用dict(hit)複製一份再加"label"，放進sources；不可改到原本的hits。
    for hit in hits:
        label = f"[來源{len(sources) + 1}]"
        part = f"{label} {hit['source']}／{hit['chunk_id']}\n{hit['text']}"

        new_text = "\n\n".join(parts + [part])

        if len(new_text) > max_chars:
            break

        parts.append(part)

        source = dict(hit)
        source["label"] = label
        sources.append(source)

    return {
        "text": "\n\n".join(parts),
        "sources": sources
    }
