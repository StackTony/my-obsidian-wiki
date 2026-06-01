
实时监控系统中哪些线程（或进程）正在特定的CPU核心上运行，并按CPU使用率排序
ps -eL -o pid,tid,psr,pcpu,comm --sort=-pcpu | awk 'NR\==1 || $3\==64'
