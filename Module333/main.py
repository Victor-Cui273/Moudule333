from test_index import load_real_docs, build_index, compare_compression, query_speed

if __name__ == "__main__":
    docs = load_real_docs('pages.jsonl')
    print(f"Loaded {len(docs)} documents")
    idx, build_time = build_index(docs)
    print(f"Index built in {build_time:.2f} sec, terms: {len(idx.index)}")
    sizes = compare_compression(idx)
    for k, v in sizes.items():
        print(f"{k}: {v/1024:.2f} KB")

    sample_term = next(iter(idx.index.keys()))
    print(f"Search for '{sample_term}': {idx.search(sample_term)[:10]}")