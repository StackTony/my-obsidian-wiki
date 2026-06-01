## 前言

文本分割器是LangChain中一个重要组建，海量的文档需要基于文本分割策略进行处理从而与大模型的各个功能模块进行交互，本篇介绍LangChain中最常用的递归字符文本分割器，包括流程分析，源码分析和实践。

---

##### 内容摘要

- 文本分割器的目的
- 递归字符文本分割器在做什么
- 递归字符文本分割器快速开始
- 递归字符文本分割器工作流程简述
- 块拆分部分源码分析
- 块合并部分源码分析

---

##### 文本分割器的目的

大模型在预训练阶段获取的知识是有限的，一般需要数据增强模块引入外部知识库，通过知识检索的方式搜索于用户提问相关的知识，而外部知识文档往往比较长，可能是包含几十页甚至几百页的内容，如果直接使用会存在以下问题

- **1.大模型处理的上下文长度有限**：大模型在预训练过程都有上下文长度限制，如果超过长度限制大模型会将超出部分丢弃，从而影响回答的性能表现
- **2.语义杂揉不利于任务检索**：长文档中各个片段的语义之前可能存在较大的差异，如果当成一个整体来做知识检索会存在语义的杂揉，应当将长文档切分成更多的小块，促使每个小块内部表意一致，块之间表意存在多样性，从而更充分的发挥知识检索的作用

因此需要引入文本分割器，它根据一定策略将文本切分为各个小块，以便适应大模型的**上下文窗口**，同时提高知识**检索的精度**。

---

##### 递归字符文本分割器在做什么

递归字符文本分割器是最常用的文本分割器，在LangChain中通过**RecursiveCharacterTextSplitter**类实现，本文介绍的是其在中文场景下更友好的版本**ChineseRecursiveTextSplitter**，其实现在Langchain-Chatchat项目工程下。  
两者的 工作流程 和目标是相同的，即指定一个块长度和一组分隔符，根据分隔符的优先顺序对文本进行预分隔，然后将小块进行合并，将大块进行递归拆分，直到获得所需的块大小，最终这些块的大小并不完全相同，但它们仍然会逼指定的块长度。

![[913b9a6ed5adeb0bafbf8ee95ab547f2.png]]

递归字符文本分割的流程简单描述

---

##### 递归字符文本分割器快速开始

我们使用Langchain-Chatchat项目下ChineseRecursiveTextSplitter，来演示如何对文本和文档的分割效果。ChineseRecursiveTextSplitter的核心源码如下

```python
class ChineseRecursiveTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(
            self,
            separators: Optional[List[str]] = None,
            keep_separator: bool = True,
            is_separator_regex: bool = True,
            **kwargs: Any,
    ) -> None:
        """Create a new TextSplitter."""
        super().__init__(keep_separator=keep_separator, **kwargs)
        self._separators = separators or [
            "\n\n",
            "\n",
            "。|！|？",
            "\.\s|\!\s|\?\s",  # 英文标点符号后面通常需要加空格
            "；|;\s",
            "，|,\s"
        ]
        self._is_separator_regex = is_separator_regex

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Split incoming text and return chunks."""
        final_chunks = []
        # Get appropriate separator to use
        separator = separators[-1]
        new_separators = []
        # TODO 先以优先级高的分隔符切分
        for i, _s in enumerate(separators):
            _separator = _s if self._is_separator_regex else re.escape(_s)
            if _s == "":
                separator = _s
                break
            if re.search(_separator, text):
                separator = _s
                new_separators = separators[i + 1:]
                break

        _separator = separator if self._is_separator_regex else re.escape(separator)
        splits = _split_text_with_regex_from_end(text, _separator, self._keep_separator)

        # Now go merging things, recursively splitting longer texts.
        _good_splits = []
        _separator = "" if self._keep_separator else separator
        for s in splits:
            # TODO 如果不超长，直接添加到中间集合good_splits,否则对之前所有的good_splits进行合并，并且对当前超长的句子也当作一个大段落，使用同样的分隔逻辑递归处理,
            # TODO 直到所有的子块都[不超长]或者[没有可分的分隔符]为止，递归停止
            # TODO 对于good_splits，虽然每个子块没有超过chunk_size，但是将他们合并之后长度可能超出了chunk_size
            if self._length_function(s) < self._chunk_size:
                _good_splits.append(s)
            else:
                if _good_splits:
                    merged_text = self._merge_splits(_good_splits, _separator)
                    final_chunks.extend(merged_text)
                    _good_splits = []
                if not new_separators:
                    # TODO 该句子虽然长超过chunk_size，但是没有可用的分隔符了，只能超过chunk_size也留下
                    final_chunks.append(s)
                else:
                    # TODO 如果还存在可用的其他分隔符，对该句子进行分解
                    other_info = self._split_text(s, new_separators)
                    # TODO 无限递归调用下去
                    final_chunks.extend(other_info)
        if _good_splits:
            merged_text = self._merge_splits(_good_splits, _separator)
            final_chunks.extend(merged_text)
        # TODO 统一换行符
        return [re.sub(r"\n{2,}", "\n", chunk.strip()) for chunk in final_chunks if chunk.strip() != ""]

```

该类继承了Langchain的RecursiveCharacterTextSplitter，因此该类也拥有split_text方法和split_documents方法，分别对应对文本分割和文档对象分割。  
以分割文本为例，我们对Python的一段介绍进行递归字符分割，该段内容包含句号，逗号，顿号等分割符

```
Python由荷兰国家数学与计算机科学研究中心的吉多·范罗苏姆于1990年代初设计，作为一门叫做ABC语言的替代品。Python提供了高效的高级数据结构，还能简单有效地面向对象编程。Python语法和动态类型，以及解释型语言的本质，使它成为多数平台上写脚本和快速开发应用的编程语言，随着版本的不断更新和语言新功能的添加，逐渐被用于独立的、大型项目的开发。

```

我们设置chunk_size=20，chunk_overlap=0，其他参数默认，分割效果如下

```powershell
>>> text_splitter = ChineseRecursiveTextSplitter(
        keep_separator=True,
        is_separator_regex=True,
        chunk_size=20,
        chunk_overlap=0
    )
>>> res = text_splitter.split_text("Python由荷...")
>>> for i in res:
        print(len(i), i)

42 Python由荷兰国家数学与计算机科学研究中心的吉多·范罗苏姆于1990年代初设计，
16 作为一门叫做ABC语言的替代品。
19 Python提供了高效的高级数据结构，
14 还能简单有效地面向对象编程。
14 Python语法和动态类型，
11 以及解释型语言的本质，
25 使它成为多数平台上写脚本和快速开发应用的编程语言，
19 随着版本的不断更新和语言新功能的添加，
17 逐渐被用于独立的、大型项目的开发。

```

从结果来看ChineseRecursiveTextSplitter会把中文文本根据常用的逗号、句号进行分割，具体使用哪些分隔符由separators参数决定，在该类中默认使用换行符，句号，问号，逗号等中文习惯中使用的分隔符，且有前后优先级关系，即初步分割优先使用前面的符号，后续再拆分使用后面的符号。

```python
self._separators = separators or [
            "\n\n",
            "\n",
            "。|！|？",
            "\.\s|\!\s|\?\s",  # 英文标点符号后面通常需要加空格
            "；|;\s",
            "，|,\s"
        ]

```

分割后每一个块的文本长度都接近指定的块大小20，结合前文所说的合并和再拆分，以第一句为例，该句长度为42，已经超出指定的大小20，理应进行再拆分，而它内部已经没有任何其他可使用的分隔符了。再看第二句，该句长度为16，小于20，理应进行和后句合并，而后句长度为19，两句合并也超出了指定块大小，因此也无法合并。此处结合这个例子先给到合并和再拆分的一个初步映像，下文会做具体的流程梳理。  
接下来我们测试使用递归字符分割器来分割文档对象，我们先使用文档加载器

```powershell
>>> from langchain_community.document_loaders import TextLoader
>>> loader = TextLoader("./text.txt", encoding="utf8")
>>> docs = loader.load()
>>> res = text_splitter.split_documents(docs)
>>> for i in res:
       print(len(i.page_content), i)

42 page_content='Python由荷兰国家数学与计算机科学研究中心的吉多·范罗苏姆于1990年代初设计，' metadata={'source': './text.txt'}
16 page_content='作为一门叫做ABC语言的替代品。' metadata={'source': './text.txt'}
19 page_content='Python提供了高效的高级数据结构，' metadata={'source': './text.txt'}
14 page_content='还能简单有效地面向对象编程。' metadata={'source': './text.txt'}
14 page_content='Python语法和动态类型，' metadata={'source': './text.txt'}
11 page_content='以及解释型语言的本质，' metadata={'source': './text.txt'}
25 page_content='使它成为多数平台上写脚本和快速开发应用的编程语言，' metadata={'source': './text.txt'}
19 page_content='随着版本的不断更新和语言新功能的添加，' metadata={'source': './text.txt'}
17 page_content='逐渐被用于独立的、大型项目的开发。' metadata={'source': './text.txt'}

```

分割的结果一样，差别在于后者的输入和输出是文档对象。

---

##### 递归字符文本分割器工作流程简述

根据前文已有的印象，递归字符文本分割器包含预分割、合并、递归拆解等步骤要素，下面给到一个更加完成的流程图。

![[b4d67ce60e7ffb36256495330a103b1a.png]]

递归字符文本分割器工作流程

其中关键要素的解释如下

- **分隔符的优先级别**：在一开始，程序尝试以最有把握的分隔符将文本进行分割，分割之后若还存在长文本，则此时只能使用其他分隔符，分隔符的优先级和语言习惯有关，中文场景下，第一优先级的分隔符是换行符，第二优先级是句号、问好、感叹号，第三优先级是分号，最后是逗号
- **chunk_size**：预先指定的块大小，最终分割的块都应该逼近这个大小，chunk_size会作为预切分之后每个块合并还是再拆分的依据
- **暂存集合**：程序会创建一个暂存集合，它按照顺序的将不超过的chunk_size的块暂存在其中，直到循环到某个超过chunk_size的块，程序以这个为信号开始一次批处理，该批处理包含暂存集合合并和大块拆解两个动作，这个暂存集合记录了本次批处理中的合并环节需要用的所有子块，这些子块可以合并为一个或者多个中等规模的块
- **重叠预留**：最简单的情况是将暂存集合合并写入结果集，然后暂存集合清空，当chunk_overlap=0时就是这种情况，而当chunk_overlap>0时，暂存集合会保留下一部分最右侧的文本，该文本会和后面的块合并，相当于会有一块重叠部分，既存在在A块，也存在在B块
- **递归拆分的停止条件**：当某块超过chunk_size，它理应被再拆解，但是前提条件是存在可用的分隔符号，我们举例最次要的分隔符是逗号，如果块中连逗号的没有则就算超长也无法再拆分，此时直接加入最终集合，更一般的情况是有分隔符可用拆分成小块，再执行合并的逻辑写入最终集合

对于合并操作也存在一个操作流程，同样采用循环每个块来决定如何操作，程序期望在不超过chunk_size的情况下聚合更多的子块，当某个块加入导致超过chunk_size时触发之前所有的块合并，额外的这些块会预留下右侧部分和之后的块合并，预留的大小由chunk_overlap控制，我们看下面这个案例

![[db893fc672488fcde4b351698c7cc7b0.png]]

重叠合并案例

每个块上的数字代表块长度大小，我们令chunk_size=50，则前4个块合并成一个中块，因为最后一个块25加入进来已经超过50，而在5，8，17，3合并之后，会从左弹出块，知道剩余的长度小于chunk_overlap，我们设chunk_overlap为5，则当退出到只剩3时满足，因此3这个块会和后面的25块以及其后的块进行合并，3块在上下两个组合中出现了2次，这样做的目的是能够**更好地保留上下文，防止不合适的短句切分了语义**。

---

##### 块拆分部分源码分析

理完了流程下面分别看下递归拆分和合并的源码实现，先看拆分部分

```python
        for s in splits:
            if self._length_function(s) < self._chunk_size:
                _good_splits.append(s)
            else:
                # TODO 拆分条件一：块超长
                if _good_splits:
                    merged_text = self._merge_splits(_good_splits, _separator)
                    final_chunks.extend(merged_text)
                    _good_splits = []
                if not new_separators:
                    # TODO 拆分条件二：有可用的分隔符
                    final_chunks.append(s)
                else:
                    # TODO 无限递归调用下去
                    other_info = self._split_text(s, new_separators)
                    final_chunks.extend(other_info)

```

拆分的代码在主流程里面，当该块超长时，判断是否还存在可用分隔符，是则递归调用该分割方法，否则直接写入最终集合，对于可用分隔符new_separators的判断已经在前文指定，具体为剔除前一轮使用过的分隔符，取此之后的分隔符，分隔符的前后顺序决定了优先级

```python
            if re.search(_separator, text):
                separator = _s
                new_separators = separators[i + 1:]
                break

```

---

##### 块合并部分源码分析

块合并的源码在子方法_merge_splits里面，源码如下

```python
    def _merge_splits(self, splits: Iterable[str], separator: str) -> List[str]:
        separator_len = self._length_function(separator)

        docs = []
        # TODO 中间过程需要维护的List
        current_doc: List[str] = []
        total = 0
        for d in splits:
            _len = self._length_function(d)
            # TODO 达到这个条件，已经达到当前可拼接的极限，再拼要超chunk_size了，之前的句子会合并拼接
            if (
                total + _len + (separator_len if len(current_doc) > 0 else 0)
                > self._chunk_size
            ):
                if total > self._chunk_size:
                    logger.warning(
                        f"Created a chunk of size {total}, "
                        f"which is longer than the specified {self._chunk_size}"
                    )
                if len(current_doc) > 0:
                    # TODO 将之前加起来长度不超过chunk_size的块拼接合并
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        # TODO 加入到最终集合
                        docs.append(doc)
                    while total > self._chunk_overlap or (
                        total + _len + (separator_len if len(current_doc) > 0 else 0)
                        > self._chunk_size
                        and total > 0
                    ):
                        # TODO 从左侧开始一个一个弹出子块，直到满足小于重叠大小，小于重叠大小的部分将保留在中间集合current_docs里面和后面的块继续组合拼接，这个重叠部分已经在上文的doc = self._join_docs(current_doc, separator)拼接合并过一次了，由于其保留在了中间集合中，因此未来还会拼接合并一次
                        total -= self._length_function(current_doc[0]) + (
                            separator_len if len(current_doc) > 1 else 0
                        )
                        # TODO 一种极端情况，当_chunk_overlap=0时，total必须减到0位置，则current_doc每次都被清空
                        current_doc = current_doc[1:]
            # TODO 在这种极端情况下，current_docs会清空之前存储的信息去合并，用下面的信息作为开头，导致两者之间没有任何重叠
            current_doc.append(d)
            # TODO 如果只有1段，不需要加分隔符
            total += _len + (separator_len if len(current_doc) > 1 else 0)
        doc = self._join_docs(current_doc, separator)
        # TODO 最后一组跳出循环的也合并进去
        # TODO 一种极端情况，所有块合并的长度都没有超过chunk_size，相当于直接拼接合并
        if doc is not None:
            docs.append(doc)
        return docs

```

其中合并的动作在

```python
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)

```

其中关键的重叠部分构造为while循环，从左侧弹出块满足chunk_overlap

```python
                    while total > self._chunk_overlap or (
                        total + _len + (separator_len if len(current_doc) > 0 else 0)
                        > self._chunk_size
                        and total > 0
                    ):
                        # TODO 从左侧开始一个一个弹出子块，直到满足小于重叠大小，小于重叠大小的部分将保留在中间集合current_docs里面和后面的块继续组合拼接，这个重叠部分已经在上文的doc = self._join_docs(current_doc, separator)拼接合并过一次了，由于其保留在了中间集合中，因此未来还会拼接合并一次
                        total -= self._length_function(current_doc[0]) + (
                            separator_len if len(current_doc) > 1 else 0
                        )
                        # TODO 一种极端情况，当_chunk_overlap=0时，total必须减到0位置，则current_doc每次都被清空
                        current_doc = current_doc[1:]

```

程序通过current_doc集合来维护合并的滑动窗口，通过total变量计数来判断何时触发合并。全文完毕。
