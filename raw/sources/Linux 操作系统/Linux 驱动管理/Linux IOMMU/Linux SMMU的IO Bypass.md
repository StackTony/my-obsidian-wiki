### SMMU的功能：
替设备将DMA请求的地址，翻译成设备真正能用的物理地址。

### IO Bypass的功能：
在开启SMMU的情况下，可以通过配置参数做到对某些硬件不使用SMMU的地址翻译功能。即硬件层面SMMU能力开启，在OS层面进行控制，使得设备直接使用物理地址来进行DMA。


### 一句话总结：
SMMU 硬件本身是上电开启、正常工作的；只是给这个设备对应的 STE（Stream Table Entry）配置成 Bypass 模式：该 SID 的 DMA 流量直接透传，不经过 Stage1/Stage2 地址翻译、不做 IOTLB 查找、不做页表权限检查。

区别：
BIOS 关掉 SMMU = 整个 SMMU 硬件不工作；
**SMMU 开启时再开启 IO Bypass = 硬件还在跑，只是这一路设备不走翻译流水线**。



### 内核配置参数（鲲鹏 / ARM）

- `iommu.passthrough=1`：全局默认 bypass，所有设备不走 SMMU 翻译
- `smmu.bypassdev=BDF`：**只对指定 PCI 设备 BDF 开启 bypass**，其他设备继续 SMMU 翻译（最常用，你问的场景）
- `disable_bypass`：关闭 bypass 能力，强制所有 SID 必须走翻译


### 模式对比

|模式|SMMU 硬件|STE 配置|设备 DMA 地址|
|---|---|---|---|
|SMMU 正常翻译|开启|正常 S1/S2|IOVA（内核维护映射）|
|SMMU 开启 + IO Bypass|开启|STE=Bypass|PA（直接透传）|
|BIOS 关闭 SMMU|关闭|不存在 STE|PA，内核走 SWIOTLB|
