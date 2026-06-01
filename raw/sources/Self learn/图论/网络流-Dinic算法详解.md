---
title: 最大流 Dinic 算法介绍
source: https://blog.nowcoder.net/n/c27155b8e2d34210b1cdfe1916e3264c
created: 2026-05-21
credibility: low
tags: [图论, 网络流, Dinic, 最大流, 层次网络, 阻塞流, 自学推荐]
---

本文转自： [https://www.cnblogs.com/linzhengmin/p/9313216.html](https://www.cnblogs.com/linzhengmin/p/9313216.html)

Dinic算法本身，自然是解决最大流(普通最大流， 最大流最小割)的算法。通过处理，也可以解决二分图的最大匹配（下文介绍），最大权闭合图。

算法介绍：介绍Dinic之前，我们先介绍一下最大流。在最大流的题目中，图被称为"网络"，每条边的边权被称作"流量"，有一个起点（源点）和一个终点（汇点）。我们要求的最大流，可以这样形象地理解：源点有一个水库，里面有无限吨水（QWQ），汇点也有一个水 库，希望得到最多的水。我们假设每个河道一天只能输水n吨（及网络流中的流量），求解汇点最多能的到几吨水。再给一个正式的定义：最大流是指网络中满足弧流量限制条件和平衡条件且具有最大流量的可行流

下面我们正式介绍Dinic：

首先引出网络流算法中的链，给个正式定义：链是网络中的一个顶点序列，这个序列中前后两个顶点有弧相连（其实我认为这个定义无关紧要，所以重点看下面弧的定义）。

弧 ：弧分为两种，第一种是前向弧是指方向和链一致的弧（简单的说就是输入的边）---前向弧，第二种弧是指方向和链不一致的弧（简单的说就是输入的边反一反）---后向弧。

好了接下来要引出一个网络流算法的 **重要概念**

**增广路**

给个正式的定义：

1、增广路是一条链

2、链上的前向弧都是非饱和弧

链上的后向弧都是非零弧

3、链是由源点到汇点的

总结一下：额...这听起来好像啥都没说(滑稽)

谈谈我的理解：

增广路就是一条从源点到汇点的路，并且带有一个值，表示该增广路的最大流量，该值得大小取决于该增广路中拥有最小流量的边。

**剩余网络**

由反向弧组成的网络，关于反向弧的权的问题，后文会介绍。

说了一大堆，下面正式介绍Dinic算法

**Dinic算法的大致步骤**

1、建立网络（包括正向弧和反向弧（初始边权为0）），将总流量置为0

2、构造层次网络（怎么又有新概念 T\_T）

简单的说，就是求出每个点u的层次，u的层次是从源点到该点的最短路径（ **注意** ：这个最短路是指弧的权都为1的情况下的最短路），若与源点不连通，层次置为-1

一遍BFS轻松解决

3、判断汇点的层次是否为-1

是：再见，算法结束，输出当前的总流量

否：下一步

4、用一次DFS完成所有增广，增广是什么呢？

增广（我的理解）：通过DFS找上述的增广路，找到了之后，将每条边的权都减去该增广路中拥有最小流量的边的流量，将每条边的反向边的权增加这个值，同时将总流量加上这个值

DFS直到找不到一条可行的从原点到汇点的路

5、goto 步骤2

细节处理，如何快速找到一条边的反向边：边的编号从0开始，反向边加在正向边之后，反向边即为该点的编号异或1

复杂度：理论上来说， **最慢** 应该是O((n^2)\*m)，n表点数，m表边数，实际上呢，应该快得不少

代码实例：（参见洛谷P3376）

传送门\[[\>洛谷<](https://www.luogu.org/problemnew/show/P3376)\] 重要提示：您的等级必须达到蓝色以上，否则后果自负

**弧优化**

在DFS的时候记录当前已经计算到第几条边了，避免重复计算。

然后在下一次构建层次网络的注意将head数组还原

### 代码

\* 使用当前弧优化

```cpp
#include <cstdio> 
#include <cstring>
#include <queue>
#include <algorithm>

using namespace std;

const int MAX = (1ll << 31) - 1;

int read(){
    int x = 0; int zf = 1; char ch = ' ';
    while (ch != '-' && (ch < '0' || ch > '9')) ch = getchar();
    if (ch == '-') zf = -1, ch = getchar();
    while (ch >= '0' && ch <= '9') x = x * 10 + ch - '0', ch = getchar(); return x * zf;
}

struct Edge{
    int to;
    int dis;
    int next;
} edges[210000];

int cur[10010], head[10010], edge_num = -1;
int n, m, s, t;

void addEdge2(int from, int to, int dis){
    edges[++edge_num].to = to;
    edges[edge_num].dis = dis;
    edges[edge_num].next = head[from];
    head[from] = edge_num;
}

void addEdge(int from, int to, int dis){
    addEdge2(from, to, dis), addEdge2(to, from, 0);
}

int d[10010];

int DFS(int u, int flow){
    if (u == t) return flow;
    int _flow = 0, __flow;
    for (int& c_e = cur[u]; c_e != -1; c_e = edges[c_e].next){
        int v = edges[c_e].to;
        if (d[v] == d[u] + 1 && edges[c_e].dis > 0){
            __flow = DFS(v, min(flow, edges[c_e].dis));
            flow -= __flow;
            edges[c_e].dis -= __flow;
            _flow += __flow;
            edges[c_e^1].dis += __flow;
            if (!flow)
                break;
        }
    }
    if (!_flow) d[u] = -1;
    return _flow;
}

bool BFS(){
    memset(d, -1, sizeof(d));
    queue<int> que; que.push(s);
    d[s] = 0; int u, _new;
    while (!que.empty()){
        u = que.front(), que.pop();
        for (int c_e = head[u]; c_e != -1; c_e = edges[c_e].next){
            _new = edges[c_e].to;
            if (d[_new] == -1 && edges[c_e].dis > 0){
                d[_new] = d[u] + 1;
                que.push(_new);
            }
        }
    }
    return (d[t] != -1);
}

void dinic(){
    int max_flow = 0;
    while (BFS()){
        for (int i = 1; i <= n; ++i) cur[i] = head[i];
        max_flow += DFS(s, MAX);
    }
    printf("%d", max_flow);
}

int main(){
    n = read(), m = read(), s = read(), t = read();
    memset(head, -1, sizeof(head));
    for (int i = 0; i < m; i++){
        int u = read(), v = read(), w = read();
        addEdge(u, v, w);
    }
    dinic();
    return 0;
}
```

### 算法主要应用场景

1、裸的最大流

2、二分图的最大匹配：建一个点S，连到二分图的集合A中；建一个点T，连到二分图的集合B中。再将所有的集合A中的点与集合B中的点相连。全部边权设为1，跑一遍最大流，结果即为二分图的最大匹配

3、最小割（定义自行百度）：在单源单汇流量图中，最大流等于最小割

4、求最大权闭合图（定义自行百度）：最大权值=正点权之和-最小割

主要问题：

　　为什么要建立反向边？

　　Answer：总结多篇博客，认为建立反向边旨在增加重新调整流的机会，即保障解是最优的（还是没有理解？可以自行百度:D）。