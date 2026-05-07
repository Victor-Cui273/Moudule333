import json
import pickle
import time
from collections import defaultdict
from compression import EliasCodec, GolombCodec

class InvertedIndex:
    def __init__(self):
        self.index = defaultdict(list)
        self.doc_count = 0

    def add_document(self, doc_id: int, tokens: list):
        """添加一篇文档，tokens 为分词后的词列表"""
        for token in set(tokens):
            self.index[token].append(doc_id)
        self.doc_count = max(self.doc_count, doc_id + 1)

    def build(self, sort=True):
        """构建完成后，对每个 posting list 排序并去重"""
        for term in self.index:
            lst = sorted(set(self.index[term]))
            self.index[term] = lst

    # 在 inverted_index.py 中替换以下两个方法

    def save_compressed(self, filepath: str, method='gamma'):
        """
        将倒排索引压缩保存到文件
        method: 'gamma', 'delta', 'golomb'
        """
        from compression import EliasCodec, GolombCodec  # 确保导入
        sorted_terms = sorted(self.index.keys())
        with open(filepath, 'wb') as f:
            # 写入词项个数，文档总数
            f.write(len(sorted_terms).to_bytes(4, 'big'))
            f.write(self.doc_count.to_bytes(4, 'big'))
            for term in sorted_terms:
                term_bytes = term.encode('utf-8')
                f.write(len(term_bytes).to_bytes(2, 'big'))
                f.write(term_bytes)
                postings = self.index[term]
                if not postings:
                    f.write((0).to_bytes(4, 'big'))  # 空列表标记
                    continue
                # 差值编码：第一个元素不变，后面每个减去前一个
                diffs = [postings[0]] + [postings[i] - postings[i - 1] for i in range(1, len(postings))]
                # 重要：将 diffs 中每个元素 +1，避免 0 值（gamma 编码要求 n>=1）
                diffs_plus1 = [d + 1 for d in diffs]
                if method == 'golomb':
                    codec = GolombCodec
                    m = 64  # 可调参数
                    data_bytes, padding = codec.encode_list(diffs_plus1, m)
                    f.write(m.to_bytes(2, 'big'))
                    f.write(padding.to_bytes(1, 'big'))
                    f.write(len(data_bytes).to_bytes(4, 'big'))
                    f.write(data_bytes)
                else:
                    # gamma 或 delta
                    data_bytes, padding = EliasCodec.encode_int_list(diffs_plus1, method=method)
                    f.write(padding.to_bytes(1, 'big'))
                    f.write(len(data_bytes).to_bytes(4, 'big'))
                    f.write(data_bytes)

    @classmethod
    def load_compressed(cls, filepath: str, method='gamma'):
        """从压缩文件加载倒排索引"""
        from compression import EliasCodec, GolombCodec
        idx = cls()
        with open(filepath, 'rb') as f:
            term_count = int.from_bytes(f.read(4), 'big')
            idx.doc_count = int.from_bytes(f.read(4), 'big')
            idx.index = {}
            for _ in range(term_count):
                term_len = int.from_bytes(f.read(2), 'big')
                term = f.read(term_len).decode('utf-8')
                if method == 'golomb':
                    m = int.from_bytes(f.read(2), 'big')
                    padding = int.from_bytes(f.read(1), 'big')
                    data_len = int.from_bytes(f.read(4), 'big')
                    data = f.read(data_len)
                    diffs_plus1 = GolombCodec.decode_bytes(data, padding, m)
                else:
                    padding = int.from_bytes(f.read(1), 'big')
                    data_len = int.from_bytes(f.read(4), 'big')
                    data = f.read(data_len)
                    diffs_plus1 = EliasCodec.decode_bytes(data, padding, method=method)
                # 恢复原始差值：每个值减 1
                diffs = [d - 1 for d in diffs_plus1]
                # 从差值重建 posting list
                postings = []
                current = 0
                for d in diffs:
                    current += d
                    postings.append(current)
                idx.index[term] = postings
        return idx

    def search(self, term: str):
        """返回包含该词项的文档 id 列表"""
        return self.index.get(term, [])

    def get_stats(self):
        """返回索引统计信息"""
        total_postings = sum(len(lst) for lst in self.index.values())
        return {
            'terms': len(self.index),
            'total_postings': total_postings,
            'avg_postings_len': total_postings / len(self.index) if self.index else 0
        }