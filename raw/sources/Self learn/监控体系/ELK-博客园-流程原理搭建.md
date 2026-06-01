---
title: ELK 流程原理及搭建
created: 2026-05-18
tags: [ELK, Elasticsearch, Logstash, Kibana, 架构]
credibility: low
source_url: https://www.cnblogs.com/hanzeng1993/p/15078477.html
---

**一，前言**

人们常常说数据如金，可是，能被利用起的数据，才是“金”。而互联网的数据，常常以日志的媒介的形式存在，并需要从中提取其中的"数据"。

从这些数据中，我们可以做用户画像（每个用户都点了什么广告，对哪些开源技术感兴趣），安全审计，安全防护（如果1小时内登录请求数到达一定值就报警），业务数据统计（如开源中国每天的博客数是多少，可视化编辑格式和markdown格式各占比例是多少）等等。

之所以能做这些，是因为用户的所有的行为，都将被记录在nginx日志中或其它web服务器的日志中。日志分析要做的就是将这些日志进行结构化，方便我们的业务人员快速查询。日志分析平台要做的就是这些。

说完这些，你是不是觉得日志分析平台很难做，需要十人的团队加班几个月才能完成？

自从有了Elasticsearch、Logstash、Kibana，俗称ELK，小公司也可以很轻松地做日志分析了。说白了，1天几G的日志，ELK完全可以吃得消。就像标题说的，只需要1个人半小时就可以搭建好了。

**二，集中式日志分析平台特点**

- 收集－能够采集多种来源的日志数据
- 传输－能够稳定的把日志数据传输到中央系统
- 存储－如何存储日志数据
- 分析－可以支持 UI 分析
- 警告－能够提供错误报告，监控机制
	ELK完美的解决上述场景。

## 三，ELK Stack 简介

ELK 不是一款软件，而是 Elasticsearch、Logstash 和 Kibana 三种软件产品的首字母缩写。这三者都是开源软件，通常配合使用，而且又先后归于 Elastic.co 公司名下，所以被简称为 ELK Stack。根据 Google Trend 的信息显示，ELK Stack 已经成为目前最流行的集中式日志解决方案。

```
Elasticsearch：分布式搜索和分析引擎，具有高可伸缩、高可靠和易管理等特点。基于 Apache Lucene 构建，能对大容量的数据进行接近实时的存储、搜索和分析操作。通常被用作某些应用的基础搜索引擎，使其具有复杂的搜索功能；

Logstash：数据收集引擎。它支持动态的从各种数据源搜集数据，并对数据进行过滤、分析、丰富、统一格式等操作，然后存储到用户指定的位置；

Kibana：数据分析和可视化平台。通常与 Elasticsearch 配合使用，对其中数据进行搜索、分析和以统计图表的方式展示；

Filebeat：ELK 协议栈的新成员，一个轻量级开源日志文件数据搜集器，基于 Logstash-Forwarder 源代码开发，是对它的替代。在需要采集日志数据的 server 上安装 Filebeat，并指定日志目录或日志文件后，Filebeat 
就能读取数据，迅速发送到 Logstash 进行解析，亦或直接发送到 Elasticsearch 进行集中式存储和分析。
```

## 四，ELK 常用架构及使用场景

### 最简单架构

在这种架构中，只有一个 Logstash、Elasticsearch 和 Kibana 实例。Logstash 通过输入插件从多种数据源（比如日志文件、标准输入 Stdin 等）获取数据，再经过滤插件加工数据，然后经 Elasticsearch 输出插件输出到 Elasticsearch，通过 Kibana 展示。详见图 1。  
图 1. 最简单架构

这种架构非常简单，使用场景也有限。初学者可以搭建这个架构，了解 ELK 如何工作。

### Logstash 作为日志搜集器

这种架构是对上面架构的扩展，把一个 Logstash 数据搜集节点扩展到多个，分布于多台机器，将解析好的数据发送到 Elasticsearch server 进行存储，最后在 Kibana 查询、生成日志报表等。详见图 2。  
图 2. Logstash 作为日志搜索器

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730095201392-1495193918.png)

这种结构因为需要在各个服务器上部署 Logstash，而它比较消耗 CPU 和内存资源，所以比较适合计算资源丰富的服务器，否则容易造成服务器性能下降，甚至可能导致无法正常工作。

### Beats 作为日志搜集器

这种架构引入 Beats 作为日志搜集器。目前 Beats 包括四种：

- Packetbeat（搜集网络流量数据）；
- Topbeat（搜集系统、进程和文件系统级别的 CPU 和内存使用情况等数据）；
- Filebeat（搜集文件数据）；
- Winlogbeat（搜集 Windows 事件日志数据）。

Beats 将搜集到的数据发送到 Logstash，经 Logstash 解析、过滤后，将其发送到 Elasticsearch 存储，并由 Kibana 呈现给用户。详见图 3。

图 3. Beats 作为日志搜集器

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730095320318-1322559557.png)

这种架构解决了 Logstash 在各服务器节点上占用系统资源高的问题。相比 Logstash，Beats 所占系统的 CPU 和内存几乎可以忽略不计。另外，Beats 和 Logstash 之间支持 SSL/TLS 加密传输，客户端和服务器双向认证，保证了通信安全。  
因此这种架构适合对数据安全性要求较高，同时各服务器性能比较敏感的场景。

### 引入消息队列机制的架构

这种架构使用 Logstash 从各个数据源搜集数据，然后经消息队列输出插件输出到消息队列中。目前 Logstash 支持 Kafka、Redis、RabbitMQ 等常见消息队列。然后 Logstash 通过消息队列输入插件从队列中获取数据，分析过滤后经输出插件发送到 Elasticsearch，最后通过 Kibana 展示。详见图 4。

图 4. 引入消息队列机制的架构

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730095515681-224038292.png)

这种架构适合于日志规模比较庞大的情况。但由于 Logstash 日志解析节点和 Elasticsearch 的负荷比较重，可将他们配置为集群模式，以分担负荷。引入消息队列，均衡了网络传输，从而降低了网络闭塞，尤其是丢失数据的可能性，但依然存在 Logstash 占用系统资源过多的问题。

### 基于 Filebeat 架构的配置部署详解

前面提到 Filebeat 已经完全替代了 Logstash-Forwarder 成为新一代的日志采集器，同时鉴于它轻量、安全等特点，越来越多人开始使用它。这个章节将详细讲解如何部署基于 Filebeat 的 ELK 集中式日志解决方案，具体架构见图 5。

图 5. 基于 Filebeat 的 ELK 集群架构

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730095609799-163785430.png)

因为免费的 ELK 没有任何安全机制，所以这里使用了 Nginx 作反向代理，避免用户直接访问 Kibana 服务器。加上配置 Nginx 实现简单的用户认证，一定程度上提高安全性。另外，Nginx 本身具有负载均衡的作用，能够提高系统访问性能。

**五，实战**

### 具体安装过程如下

- 步骤 1，安装 JDK
- 步骤 2，安装 Elasticsearch
- 步骤 3，安装 Kibana
- 步骤 4，安装 Nginx
- 步骤 5，安装 Logstash
- 步骤 6，配置 Logstash
- 步骤 7，安装 Logstash-forwarder
- 步骤 8，最终验证

### 安装前的准备

1. 两台 64 位虚拟机，操作系统是 Ubuntu 14.04，2 CPU，4G 内存，30G 硬盘
2. 两台 64 位虚拟机，操作系统是 CentOS 7.1，2 CPU，4G 内存，30G 硬盘
3. 创建用户 elk 和组 elk，以下所有的安装均由这个用户操作，并授予 sudo 权限
4. 如果是 CentOS，还需要配置官方 YUM 源，可以访问 CentOS 软件包

**注意：** 以下所有操作都是在两个平台上完成。

### 步骤 1，安装 JDK

Elasticsearch 要求至少 Java 7。一般推荐使用 Oracle JDK 1.8 或者 OpenJDK 1.8。我们这里使用 OpenJDK 1.8。

**Ubuntu 14.04**

加入 Java 软件源（Repository）

```
$ sudo add-apt-repository ppa:openjdk-r/ppa
```

更新系统并安装 JDK

```
$ sudo apt-get update 
$ sudo apt-get install openjdk-8-jdk
```

验证 Java

```
$ java -version
openjdk version "1.8.0_45-internal"
OpenJDK Runtime Environment (build 1.8.0_45-internal-b14)
OpenJDK 64-Bit Server VM (build 25.45-b02, mixed mode)
```

**CentOS 7.1**

**配置 YUM 源**

```
$ cd /etc/yum.repos.d
$ sudo vi centos.repo
```

**加入以下内容**

```
[base]
name=CentOS-$releasever - Base
mirrorlist=http://mirrorlist.centos.org/?release=$releasever&arch=$basearch&repo=os&infra=$infra
#baseurl=http://mirror.centos.org/centos/$releasever/os/$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
#released updates 
[updates]
name=CentOS-$releasever - Updates
mirrorlist=http://mirrorlist.centos.org/?release=$releasever&arch=$basearch&repo=updates&infra=$infra
#baseurl=http://mirror.centos.org/centos/$releasever/updates/$basearch/
gpgcheck=1
gpgkey=<a href="../../../../../etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7"><code>file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7</code></a>
```

**安装 JDK**

```
$ sudo yum install java-1.8.0-openjdk
```

**验证 Java**

```
$ java -version
openjdk version "1.8.0_65"
OpenJDK Runtime Environment (build 1.8.0_65-b17)
OpenJDK 64-Bit Server VM (build 25.65-b01, mixed mode)
```

### 步骤 2，安装 Elasticsearch

**Ubuntu 14.04**

**下载 Elasticsearch 软件**

```
$wget https://download.elasticsearch.org/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/2.1.0/elasticsearch-2.1.0.tar.gz
```

**解压**

```
$ tar xzvf elasticsearch-2.1.0.tar.gz
```

文件目录结构如下：

```
$ pwd
/home/elk/elasticsearch-2.1.0
$ ls
bin config lib LICENSE.txt NOTICE.txt README.textile
```

**修改配置文件**

```
$ cd config
$ vi elasticsearch.yml
```

找到 # network.host 一行，修改成以下：

```
network.host: localhost
```

**启动 elasticsearch**

```
$ cd ../bin
$ ./elasticsearch
```

**验证 elasticsearch**

```
$ curl 'localhost:9200/'
{
 "name" : "Surge",
 "cluster_name" : "elasticsearch",
 "version" : {
 "number" : "2.1.0",
 "build_hash" : "72cd1f1a3eee09505e036106146dc1949dc5dc87",
 "build_timestamp" : "2015-11-18T22:40:03Z",
 "build_snapshot" : false,
 "lucene_version" : "5.3.1"
 },
 "tagline" : "You Know, for Search"
}
```

**CentOS 7.1**

步骤和上述 Ubuntu 14.04 安装完全一致

### 步骤 3，安装 Kibana

**Ubuntu 14.04**

**下载 Kibana 安装软件**

```
$ wget https://download.elastic.co/kibana/kibana/kibana-4.3.0-linux-x64.tar.gz
```

**解压**

```
$ tar xzvf kibana-4.3.0-linux-x64.tar.gz
```

文件目录结构如下：

```
$ pwd
/home/elk/kibana-4.3.0-linux-x64
$ ls
bin config installedPlugins LICENSE.txt node node_modules optimize 
                               package.json README.txt src webpackShims
```

**修改配置文件**

```
$ cd config
$ vi kibana.yml
```

找到 # server.host，修改成以下：

```
server.host:“localhost”
```

**启动 Kibana**

```
$ cd ../bin
$ ./kibana
[…]
 log [07:50:29.926] [info][listening] Server running at http://localhost:5601
[…]
```

**验证 Kibana**

由于我们是配置在 localhost，所以是无法直接访问 Web 页面的。

可以使用 netstat 来检查缺省端口 5601，或者使用 curl：

```
$ curl localhost:5601
<script>var hashRoute = '/app/kibana';
var defaultRoute = '/app/kibana';
 
var hash = window.location.hash;
if (hash.length) {
 window.location = hashRoute + hash;
} else {
 window.location = defaultRoute;
}</script>
```

**CentOS 7.1**

步骤和上述 Ubuntu 14.04 安装完全一致。

### 步骤 4，安装 Nginx

Nginx 提供了反向代理服务，可以使外面的请求被发送到内部的应用上。

**Ubuntu 14.04**

**安装软件**

```
$ sudo apt-get install nginx apache2-utils
```

**修改 Nginx 配置文件**

```
$ sudo vi /etc/nginx/sites-available/default
```

找到 server\_name，修改成正确的值。或者使用 IP，或者使用 FQDN。

然后在加入下面一段内容：

```
server {
 listen 80;
 server_name example.com;
 location / {
 proxy_pass http://localhost:5601;
 proxy_http_version 1.1;
 proxy_set_header Upgrade $http_upgrade;
 proxy_set_header Connection 'upgrade';
 proxy_set_header Host $host;
 proxy_cache_bypass $http_upgrade; 
 ｝
 }
```

**注意** ：建议使用 IP。

**重启 Nginx 服务**

```
$ sudo service nginx restart
```

**验证访问**

http://FQDN 或者 http://IP

**CentOS 7.1**

**配置 Nginx 官方 yum 源**

```
$ sudo vi /etc/yum.repos.d/nginx.repo
[nginx]
name=nginx repo
baseurl=http://nginx.org/packages/centos/7/$basearch/
gpgcheck=0
enabled=1
```

**安装软件**

```
$ sudo yum install nginx httpd-tools
```

**修改 Nginx 配置文件**

```
$ sudo vi /etc/nginx/nginx.conf
```

检查是否 http 块（http{...}）含有下面这一行：

```
include /etc/nginx/conf.d/*conf
```

**为 Kibana 创建一个配置文件**

```
$ sudo vi /etc/nginx/conf.d/kibana.conf
```

加入以下这一段内容：

```
server {
 listen 80;
 
 server_name example.com;
 
 location / {
 proxy_pass http://localhost:5601;
 proxy_http_version 1.1;
 proxy_set_header Upgrade $http_upgrade;
 proxy_set_header Connection 'upgrade';
 proxy_set_header Host $host;
 proxy_cache_bypass $http_upgrade; 
 }
｝
```

**注意** ：建议使用 IP。

**启动 Nginx 服务**

```
$ sudo systemctl enable nginx
$ sudo systemctl start nginx
```

**验证访问**

http://FQDN 或者 http://IP

### 步骤 5，安装 Logstash

**Ubuntu 14.04**

**下载 Logstash 安装软件**

```
$ wget https://download.elastic.co/logstash/logstash/logstash-2.1.1.tar.gz
```

**解压**

```
$ tar xzvf logstash-2.1.1.tar.gz
```

文件目录结构如下：

```
$ pwd
/home/elk/logstash-2.1.1
 
$ ls
bin CHANGELOG.md CONTRIBUTORS Gemfile Gemfile.jruby-1.9.lock lib LICENSE NOTICE.TXT vendor
```

**验证 Logstash**

```
$ cd bin
$ ./logstash -e 'input { stdin { } } output { stdout {} }'
Settings: Default filter workers: 1
Logstash startup completed
```

显示如下：

```
hello elk stack
2015-12-14T01:17:24.104Z 0.0.0.0 hello elk stack
```

说明 Logstash 已经可以正常工作了。按 **CTRL-D** 退出

**CentOS 7.1**

步骤和上述 Ubuntu 14.04 安装完全一致。

### 步骤 6，配置 Logstash

我们需要配置 Logstash 以指明从哪里读取数据，向哪里输出数据。这个过程我们称之为定义 Logstash 管道（Logstash Pipeline）。

通常一个管道需要包括必须的输入（input），输出（output），和一个可选项目 Filter。见图 7。

##### 图 7.Logstash 管道结构示意

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730102336747-1383976416.png)

标准的管道配置文件格式如下：

```
# The # character at the beginning of a line indicates a comment. Use
# comments to describe your configuration.
input {
}
# The filter part of this file is commented out to indicate that it is
# optional.
#filter {
#}
output {
}
```

每一个输入/输出块里面都可以包含多个源。Filter 是定义如何按照用户指定的格式写数据。

由于我们这次是使用 logstash-forwarder 从客户机向服务器来传输数据，作为输入数据源。所以，我们首先需要配置 SSL 证书（Certification）。用来在客户机和服务器之间验证身份。

**Ubuntu 14.04**

**配置 SSL**

```
$ sudo mkdir -p /etc/pki/tls/certs etc/pki/tls/private
$ sudo vi /etc/ssl/openssl.cnf
```

找到 \[v3\_ca\] 段，添加下面一行，保存退出。

```
subjectAltName = IP: logstash_server_ip
```

执行下面命令：

```
$ cd /etc/pki/tls
$ sudo openssl req -config /etc/ssl/openssl.cnf -x509 -days 3650 -batch -nodes -newkey rsa:2048 -keyout 
         private/logstash-forwarder.key -out certs/logstash-forwarder.crt
```

**配置 Logstash 管道文件**

```
$ cd /home/elk/logstash-2.1.1
$ mkdir conf
$ vi simple.conf
```

添加以下内容：

```
input {
 lumberjack {
 port => 5043
 type => "logs"
 ssl_certificate => "/etc/pki/tls/certs/logstash-forwarder.crt"
 ssl_key => "/etc/pki/tls/private/logstash-forwarder.key"
 }
}
filter {
 grok {
 match => { "message" => "%{COMBINEDAPACHELOG}" }
 }
 date {
 match => [ "timestamp" , "dd/MMM/yyyy:HH:mm:ss Z" ]
 }
}
output {
 elasticsearch { hosts => ["localhost:9200"] }
 stdout { codec => rubydebug }
}
```

**启动 Logstsh**

```
$ cd /home/elk/logstash-2.1.1/bin
$ ./logstash -f ../conf/simple.conf
```

**CentOS 7.1**

**在 CentOS 7.1 上配置 Logstash，只有一步配置 SSL 是稍微有点不同，其他全部一样。**

```
$ sudo vi /etc/pki/tls/openssl.cnf
```

找到 \[v3\_ca\] 段，添加下面一行，保存退出。

```
subjectAltName = IP: logstash_server_ip
 
$ cd /etc/pki/tls
$ sudo openssl req -config /etc/pki/tls/openssl.cnf -x509 -days 3650 -batch -nodes -newkey 
         rsa:2048 -keyout private/logstash-forwarder.key -out certs/logstash-forwarder.crt
```

这里产生的 logstash-forwarder.crt 文件会在下一节安装配置 Logstash-forwarder 的时候使用到。

### 步骤 7，安装 Logstash-forwarder

**注意** ：Logstash-forwarder 也是一个开源项目，最早是由 lumberjack 改名而来。在作者写这篇文章的时候，被吸收合并到了 Elastic.co 公司的另外一个产品 Beat 中的 FileBeat。如果是用 FileBeat，配置稍微有些不一样，具体需要去参考官网。

**Ubuntu14.04**

**安装 Logstash-forwarder 软件**

**注意：** Logstash-forwarder 是安装在另外一台机器上。用来模拟客户机传输数据到 Logstash 服务器。

**配置 Logstash-forwarder 安装源**

执行以下命令：

```
$ echo 'deb http://packages.elastic.co/logstashforwarder/debian 
                  stable main' | sudo tee /etc/apt/sources.list.d/logstashforwarder.list
```

```
$ wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
```

**安装软件包**

```
$ sudo apt-get update
$ sudo apt-get install Logstash-forwarder
```

**配置 SSL**

```
$ sudo mkdir -p /etc/pki/tls/certs
```

把在步骤六中在 Logstash 服务器上产生的 ssl 证书文件拷贝到刚刚创建出来的目录下：

```
$ sudo scp user@logstash_server:/etc/pki/tls/certs/logstash_forwarder.crt /etc/pki/tls/certs/
```

**配置 Logstash-forwarder**

```
$ sudo vi /etc/logstash-forwarder.conf
```

在 network 段（"network": {），修改如下：

```
"servers": [ "logstash_server_private_address:5043" ],
"ssl ca": "/etc/pki/tls/certs/logstash-forwarder.crt",
"timeout": 15
```

在 files 段（"files": \[），修改如下：

```
{
"paths": [
 "/var/log/syslog",
 "/var/log/auth.log"
 ],
 "fields": { "type": "syslog" }
}
```

**启动 Logstash-forwarder**

```
$ sudo service logstash-forwarder start
```

**验证 Logstash-forwarder**

```
$ sudo service logstash-forwarder status
logstash-forwarder is running
```

**CentOS 7.1**

**配置 Logstash-forwarder 安装源**

执行以下命令：

```
$ sudo rpm --import http://packages.elastic.co/GPG-KEY-elasticsearch
 
$ sudo vi /etc/yum.repos.d/logstash-forwarder.repo
```

加入以下内容：

```
[logstash-forwarder]
name=logstash-forwarder repository
baseurl=http://packages.elastic.co/logstashforwarder/centos
gpgcheck=1
gpgkey=http://packages.elasticsearch.org/GPG-KEY-elasticsearch
enabled=1
```

存盘退出。

**安装软件包**

```
$ sudo yum -y install logstash-forwarder
```

剩余步骤和上述在 Ubuntu 14.04 上面的做法完全一样。

### 步骤 8，最后验证

在前面安装 Kibana 的时候，曾经有过验证。不过，当时没有数据，打开 Web 页面的时候，将如下所示：

##### 图 8. 无数据初始页面

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730103134922-747293619.png)

现在，由于 logstash-forwarder 已经开始传输数据了，再次打开 Web 页面，将如下所示：

##### 图 9. 配置索引页面

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730103147274-405309721.png)

点击创建按钮（Create），在选择 Discover，可以看到如下画面：

##### 图 10. 数据展示页面

![](https://img2020.cnblogs.com/blog/1461883/202107/1461883-20210730103158103-1313440724.png)

至此，所有部件的工作都可以正常使用了。关于如何具体使用 Kibana 就不在本文中加以描述了，有兴趣的同学可以参考官网。

文章参考出处：

https://my.oschina.net/zjzhai/blog/751246

https://www.zybuluo.com/dume2007/note/665868

https://www.ibm.com/developerworks/cn/opensource/os-cn-elk/index.html

相关阅读：
https://mp.weixin.qq.com/s/TEOI7DNHGo6Z3jNMRGKnqw