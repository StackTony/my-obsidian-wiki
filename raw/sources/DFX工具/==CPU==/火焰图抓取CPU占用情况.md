
#### 火焰图抓取CPU占用情况

<span style='color:#333333'>perf record -F 99 -p your_pid -g -- sleep 60</span>
<span style='color:#333333'>perf script \> out.perf</span>
<span style='color:#333333'>/opt/FlameGraph/stackcollapse-perf.pl out.perf \> out.folded</span>
<span style='color:#333333'>/opt/FlameGraph/flamegraph.pl out.folded \> cpu.svg</span>

<span style='color:#333333'>perf record -g -a -- sleep 30</span>
<span style='color:#333333'>perf record -C 33-38 -g -a -- sleep 20</span>
<span style='color:#333333'>perf script -i perf.data \> perf.unfold</span>
<span style='color:#333333'>./FlameGraph-master/stackcollapse-perf.pl perf.unfold \> perf.folded</span>
<span style='color:#333333'>./FlameGraph-master/flamegraph.pl perf.folded \> perf.svg</span>
