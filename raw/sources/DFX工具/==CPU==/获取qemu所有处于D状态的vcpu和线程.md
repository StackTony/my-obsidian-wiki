
**获取qemu所有处于D状态的vcpu和线程**

ps -eL -o pid,tid,psr,state,comm,cmd \| grep -E '(KVM\|qemu)' \| grep -v grep \| grep "D "
