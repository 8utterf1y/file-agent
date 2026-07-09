对于题目3，我是否需要理解设计文档的格式
是的，题目3中的"设计文档"主要指的是 RFC 文档（如 RFC 4861、RFC 8200 等协议规范），而不是项目设计文档。

从你之前看到的 benchmark.md，参考的RFC包括：

RFC	主题
RFC 4861	Neighbor Discovery for IPv6
RFC 8200	Internet Protocol, Version 6 (IPv6) Specification
RFC 2710	Multicast Listener Discovery (MLD)
RFC 8415	DHCPv6
RFC 文档格式你需要理解的关键点：

MUST/SHOULD/MAY 关键字（RFC 2119定义）：
MUST = 绝对要求
SHOULD = 推荐，但在特殊情况下可以忽略
MAY = 可选
Section 结构：每个RFC都有明确的章节划分，如 §6.3.4 Router Discovery
Normative vs Informative：
Normative 文本是必须遵守的规范
通常用 "MUST", "SHOULD", "MAY" 等词标识
从 issues 清单来看，每个issue都明确标注了：

违反的是 MUST/SHOULD/MAY 中的哪一个
具体是哪个 RFC 的哪个 Section
源码路径（如 freebsd/netinet6/nd6.c）
建议：你可以详细阅读 Difference/issues/01-nd-option-limit.md，它完整展示了问题分析格式，理解后你可以设计出通用的比对流程。

需要我帮你梳理RFC规范的关键格式要点吗？

如果我要写这个，必须知道的有关rfc文档以及代码的有哪些信息
基于已有的材料，你需要掌握以下内容：

RFC 文档必须了解的信息
1. 关键词定义（RFC 2119）
关键词	含义	违规级别
MUST	绝对要求	严重
MUST NOT	禁止	严重
SHOULD	推荐，但有理由可忽略	中等
SHOULD NOT	不推荐，但有理由可做	中等
MAY	可选	轻微
2. 你需要关注的 RFC 条款（从 benchmark.md）
RFC	关键章节	涉及问题
RFC 4861	§6.3.4 Router Discovery, §7.2.6/7.2.8 Proxy NA, §4.6.2 Option Processing	ND option limit, Proxy NA delay/unsolicited
RFC 8200	§4, §4.5 Fragmentation	Fragment chain walking
RFC 8415	DHCPv6 whole	No DHCPv6 support
RFC 2710	MLD whole	MLD multicast reception
3. RFC 结构快速定位
Section 4/6/7 通常是协议帧格式和处理规则
Normative text 通常包含上述关键词
Implementor's notes 包含已知实现差异
代码必须了解的信息
1. F-Stack 代码结构
freebsd/netinet6/
├── nd6.c          # Neighbor Discovery 主逻辑
├── nd6_nbr.c      # Neighbor 发现相关
└── ...
dpdk/lib/ip_frag/
└── rte_ip_frag.h  # IP分片处理
2. 已知的 6 个 issues 对应代码位置
Issue	文件	行号	问题本质
ND option limit	freebsd/netinet6/nd6.c	105, 508	nd6_maxndopt = 10 硬编码限制
Proxy NA no random delay	freebsd/netinet6/nd6_nbr.c	-	代理NA缺少随机延迟
Proxy NA no unsolicited	freebsd/netinet6/nd6_nbr.c	-	代理NA缺少 unsolicited NA
Fragment chain walking	dpdk/lib/ip_frag/rte_ip_frag.h	-	分片链未完整遍历
No DHCPv6 support	整个模块缺失	-	功能缺失
MLD misrouted via KNI	lib/ff_dpdk_if.c	-	MLD路由错误
3. C 代码分析关键点
变量声明：VNET_DEFINE_STATIC(int, nd6_maxndopt) = 10
条件判断：if (i > V_nd6_maxndopt)
循环遍历：for (; limit > 0; limit -= optlen)
宏定义：如 ICMP6STAT_INC
你需要编写的检测逻辑
输入: RFC文档 + 代码仓库
↓
1. 解析RFC提取 MUST/SHOULD/MAY 条款
   - 关键词正则匹配
   - Section编号提取
   - 条款内容存储
↓
2. 解析C代码提取协议实现
   - 函数定义识别
   - 条件判断提取
   - 硬编码值识别
↓
3. 规则匹配
   - RFC条款 ← → 代码实现
   - 检测 MUST 违规 → 高优先级
   - 检测 SHOULD 违规 → 中优先级
↓
输出: issues列表 + 证据链
