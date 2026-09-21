原文： https://zhuanlan.zhihu.com/p/575667017

今天分享一个内核调试实用工具——[devmem](https://zhida.zhihu.com/search?content_id=216058721&content_type=Article&match_order=1&q=devmem&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTA5ODEsInEiOiJkZXZtZW0iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMTYwNTg3MjEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.jr8cXwnjpOnmRtr8uLdgjIaYYYAwbLjDCkoUhb0JxuI&zhida_source=entity)。

相信很多做底层驱动的人都会经常用到。

在Linux系统，如果我们想要访问某个寄存器，就需要写一个[驱动程序](https://zhida.zhihu.com/search?content_id=216058721&content_type=Article&match_order=1&q=%E9%A9%B1%E5%8A%A8%E7%A8%8B%E5%BA%8F&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTA5ODEsInEiOiLpqbHliqjnqIvluo8iLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMTYwNTg3MjEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.cUHQPgKmh2m94Ohh9C71mstiiyBaPkBL3BsKYqJoaR0&zhida_source=entity)，在驱动中映射寄存器地址，转为[虚拟地址](https://zhida.zhihu.com/search?content_id=216058721&content_type=Article&match_order=1&q=%E8%99%9A%E6%8B%9F%E5%9C%B0%E5%9D%80&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTA5ODEsInEiOiLomZrmi5_lnLDlnYAiLCJ6aGlkYV9zb3VyY2UiOiJlbnRpdHkiLCJjb250ZW50X2lkIjoyMTYwNTg3MjEsImNvbnRlbnRfdHlwZSI6IkFydGljbGUiLCJtYXRjaF9vcmRlciI6MSwiemRfdG9rZW4iOm51bGx9.mpE-FOs1O1_MyfjXjerktPBNfbIwYI0sxIieIlReYXc&zhida_source=entity)后就可以访问。

但有时候，我们只是单纯想知道某个寄存器的值，不想这么麻烦，怎么办呢？

Linux早就想到这一点了，于是提供了一个工具devmem，通过devmem就可以直接读写寄存器，

devmem是一个命令，在shell中输入devmem命令就可以非常方便的读写寄存器。

## **如何使用devmem？**

devmem命令格式：

```
Usage: devmem ADDRESS [WIDTH [VALUE]]

Read/write from physical address

 ADDRESS Address to act upon
 WIDTH Width (8/16/...)
 VALUE Data to be written
```

ADDRESS：物理地址

WIDTH：位宽，32位、64位等等

VALUE：要写入的值

例如，读取32位寄存器0x40200000的值：

向32位寄存器0x40200000写入0x12345678

```
devmem 0x40200000 32 0x12345678
```

可以看到，devmem的使用非常简单，有了devmem就可以轻松访问寄存器。

## **内核配置devmem**

devmem命令依赖于[/dev/mem](https://zhida.zhihu.com/search?content_id=216058721&content_type=Article&match_order=1&q=%2Fdev%2Fmem&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTA5ODEsInEiOiIvZGV2L21lbSIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjIxNjA1ODcyMSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.qwjDHyNUKi8S2VXqTNjaCej0pHNeO9Zt3Ft-DNLaZcE&zhida_source=entity)设备节点，需要在[Linux内核](https://zhida.zhihu.com/search?content_id=216058721&content_type=Article&match_order=1&q=Linux%E5%86%85%E6%A0%B8&zd_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ6aGlkYV9zZXJ2ZXIiLCJleHAiOjE3OTAxNTA5ODEsInEiOiJMaW51eOWGheaguCIsInpoaWRhX3NvdXJjZSI6ImVudGl0eSIsImNvbnRlbnRfaWQiOjIxNjA1ODcyMSwiY29udGVudF90eXBlIjoiQXJ0aWNsZSIsIm1hdGNoX29yZGVyIjoxLCJ6ZF90b2tlbiI6bnVsbH0.aADSA74nwEDdoPzziliCdaNm_szqYTMLCfsTmkM14hM&zhida_source=entity)中打开/dev/mem的配置：

```
Device Drivers  --->
   Character devices  --->
      [*] /dev/mem virtual device support
```

![](https://pic3.zhimg.com/v2-a5df065aac3c6d95776512f806627110_1440w.jpg)

## **Linux应用层操作寄存器**

除了直接使用devmem，我们也可以在Linux应用层自己实现一个devmem。

devmem的实现原理，就是打开/dev/mem，然后通过mmap映射物理地址，从而实现读写寄存器。因此，我们只要实现这些操作，就可以自己实现类似devmem的功能。

例如，在Linux应用层读取物理地址为0x40000000的值：

```
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>

#define MAP_SIZE 0x80000
#define base 0x40000000

int main(int argc, char **argv)
{
 int fd = open("/dev/mem",O_RDWR|O_NDELAY);
    
    if (fd < 0)
    {
        printf("open /dev/mem error!\n");
        return -1;
 }
    
    void *map_base = mmap(NULL,MAP_SIZE,PROT_READ|PROT_WRITE,MAP_SHARED,fd,base);
    if (map_base == MAP_FAILED)
    return -1;
    
    printf("%x \n",*(volatile unsigned int*)(map_base));

    close(fd);
    munmap(map_base,MAP_SIZE);
    
 return 0;
}
```

## **总结**

devmem是一个很常用的工具，主要给驱动开发人员在Linux应用层调试使用。devmem不仅仅是访问寄存器，只要有权限访问某个物理地址，就可以使用devmem，方便我们调试。