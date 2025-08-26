### 概述
|接口名称|计划下发|PrimaryProcessingWorkPlan|
|----|----|----|
|接口方式|异步|nan|
|||
|系统类型|系统名称|接口协议（SOAP/JDBC）|
|源系统|APS|SOAP|
|目标系统|MES|SOAP|
|||
|||
|||
|||
|||
|||
|说明：选择异步方式时可不填返回数据结构和返回的数据映射关系|nan|nan|

### 源系统发送数据结构
|结构编号|名称|描述|字段类型|字段描述|occurrence|缺省值|备注|
|----|----|----|----|----|----|----|----|
|1|WorkPlans|nan|nan|nan|1|nan|nan|
|1.1|Plan|nan|nan|nan|1..n|nan|nan|
|1.1.1|PlanID|计划ID|字符|H+工单类型（2位）+流水码（9位，前补零），<br>例:HHS000000001 杭州混丝工单；<br>HS-混丝，YP-叶片，YS-叶丝，WS-喂丝，JB-卷包|1|nan|喂丝机和卷包机有计划更新的情况，制丝没有|
|1.1.2|ProductionLine|工序段|字符|如果是制丝计划：一个制丝生产线(CP1)<br>如果是喂丝机计划：多个喂丝机代码(W1)<br>如果是卷包计划：一个机组(A1)|1..n|nan|nan|
|1.1.3|BatchCode|批次号|字符|卷包，喂丝没有<br>日期8位<br>工段1位<br>班别1位<br>批次顺序1位<br>预留1位<br>制丝批次号：20110317A220|0..1|nan|nan|
|1.1.4|MaterialCode|生产的物料代码|字符|卷包，牌号<br>制丝，叶片，叶丝，成丝<br>喂丝，成丝|1|nan|nan|
|1.1.5|BOMRevision|版本号|字符串|卷包，喂丝没有<br>制丝是大版本|0..1|nan|nan|
|1.1.6|Quantity|计划生产量|字符串|叶片，叶丝投入产出一样<br>成丝表示叶组投料量，不包括掺配物<br>喂丝，没有<br>卷包，成品烟产量|0..1|nan|nan|
|1.1.7|PlanStartTime|计划开始时间|字符串|日期，YYYY/MM/DD hh:mm:ss|1|nan|nan|
|1.1.8|PlanEndTime|计划结束时间|字符串|日期，YYYY/MM/DD hh:mm:ss|1|nan|nan|
|1.1.9|Sequence|执行顺序|字符串|整型|1|nan|卷包发生同一天内的切换，1开始<br>制丝班次内开始|
|1.1.10|Shift|班次|字符串|卷包，喂丝没有<br>1-早/2-中/3-晚|0..1|nan|nan|
|1.1.11|InputBatch|nan|nan|nan|0..n|nan|卷包：喂丝机 1<br>喂丝：成丝   0<br>成丝：叶丝   1..n<br>回用烟丝2:  0..n<br>叶丝：叶片   1<br>叶片：       0|
|1.1.11.1.1|InputPlanID|前工序计划号|字符串|nan|0..1|nan|当指定批次的物料不是通过计划进行生产的，比如回用烟丝二|
|1.1.11.1.2|InputBatchCode|前工序批次号|字符串|nan|0..1|nan|指定批次号|
|1.1.11.1.3|Quantity|数量|字符串|卷包，喂丝没有|0..1|nan|nan|
|1.1.11.1.4|BatchSequence|批次顺序|字符串|卷包，喂丝没有|0..1|nan|nan|
|1.1.11.1.5|IsWholeBatch|是否整批|字符串|bool,false or true|0..1|nan|卷包，喂丝没有|
|1.1.11.1.6|IsMainChannel|是否走主通道|字符串|bool,false or true|0..1|1.0|nan|nan|
|1.1.11.1.7|IsDeleted|是否删除|字符串|bool,false or true|0..1|nan|用于喂丝机工单取消追加|
|1.1.11.1.8|IsLastOne|是否最后一个批次|字符串|bool,false or true|0..1|nan|只有喂丝才需要|
|1.1.11.1.9|MaterialCode|物料代码|字符串|nan|1|nan|nan|
|1.1.11.1.10|BOMRevision|版本号|字符串|nan|1|nan|nan|
|1.1.11.1.11|Tiled  |是否平铺|字符串|bool,false or true|0..1|nan|只有回用烟丝二才会给出是否平铺|
|1.1.12|IsVaccum|是否真空回潮|字符串|bool,false or true|0..1|nan|叶片计划|
|1.1.13|IsSH93|是否走SH93|字符串|bool,false or true|0..1|nan|叶丝计划|
|1.1.14|IsHDT|是否走HDT|字符串|bool,false or true|0..1|nan|叶丝计划|
|1.1.15|IsFlavor|是否补香|字符串|bool,false or true|0..1|nan|叶丝计划|
|1.1.16|Unit|基本单位|字符串|从主数据获取|1|nan|nan|
|1.1.17|PlanDate|计划日期|字符串|计划班次开始日期，YYYY/MM/DD|1|nan|nan|
|1.1.18|PlanOutputQuantity|计划产出量|字符串|计划产出量，混丝计划中必需|0..1|nan|nan|
|1.1.19|IsOutsourcing|是否委外|字符串|true or false|1|nan|只有混丝可能为true，其余皆为false|
|1.1.20|IsBackup|是否备份工单|字符串|true or false|0..1|nan|只有卷包计划会有这个字段|
| | | | | | | | |
|填表说明：| | | | | | | |
|1. 结构编号：以树形结构编号方式，即第一层为1，2,3…第二层为1.1,1.2,2.1…。| | | | | | | |
|2.名称：即字段的命名| | | | | | | |
|3.字段类型：intger、string、dateTime、boolean、float、bit、double、blob等等| | | | | | | |
|4.occurrence:1、1…unbounded、0..1、0..unbounded等四种，（1：表示该节点有且只有一次，1…unbounded：表示该节点将循环出现一次以上，0..1：表示该节点可能不出现也有可能出现一次；0..unbounded：表示该节点可能不出现也有可能循环出现多次）| | | | | | | |
|5. 缺省值：即需平台提供的默认值。| | | | | | | |

### 源系统返回数据结构
|结构编号|名称|描述|字段类型|字段描述|occurrence|缺省值|
|----|----|----|----|----|----|----|
|1|Result|结果|字符串|枚举,1-成功，2-失败|1|nan|
|2|Reason|原因|字符串|nan|0..1|nan|
| | | | | | | |
|填表说明：| | | | | | | |
|1. 结构编号：以树形结构编号方式，即第一层为1，2,3…第二层为1.1,1.2,2.1…。| | | | | | | |
|2.名称：即字段的命名| | | | | | | |
|3.字段类型：intger、string、dateTime、boolean、float、bit、double、blob等等| | | | | | | |
|4.occurrence:1、1…unbounded、0..1、0..unbounded等四种，（1：表示该节点有且只有一次，1…unbounded：表示该节点将循环出现一次以上，0..1：表示该节点可能不出现也有可能出现一次；0..unbounded：表示该节点可能不出现也有可能循环出现多次）| | | | | | | |

### 目标系统接收数据结构
|结构编号|名称|描述|字段类型|字段描述|occurrence|缺省值|备注|
|----|----|----|----|----|----|----|----|
|1|Plan|nan|nan|nan|1..n|nan|nan|
|1.1|PlanID|计划ID|字符|H+工单类型（2位）+流水码（9位，前补零），<br>例:HHS000000001 杭州混丝工单；<br>HS-混丝，YP-叶片，YS-叶丝，WS-喂丝，JB-卷包|1|nan|喂丝机和卷包机有计划更新的情况，制丝没有|
|1.2|ProductionLine|工序段|字符|如果是制丝计划：一个制丝生产线(CP1)<br>如果是喂丝机计划：多个喂丝机代码(W1)<br>如果是卷包计划：一个机组(A1)|1..n|nan|nan|
|1.3|BatchCode|批次号|字符|卷包，喂丝没有<br>日期8位<br>工段1位<br>班别1位<br>批次顺序1位<br>预留1位<br>制丝批次号：20110317A220|0..1|nan|nan|
|1.4|MaterialCode|生产的物料代码|字符|卷包，牌号<br>制丝，叶片，叶丝，成丝<br>喂丝，成丝|1|nan|nan|
|1.5|BOMRevision|版本号|字符串|卷包，喂丝没有<br>制丝是大版本|0..1|nan|nan|
|1.6|Quantity|计划生产量|字符串|叶片，叶丝投入产出一样<br>成丝表示叶组投料量，不包括掺配物<br>喂丝，没有<br>卷包，成品烟产量|0..1|nan|nan|
|1.7|PlanStartTime|计划开始时间|字符串|日期，YYYY/MM/DD hh:mm:ss|1|nan|nan|
|1.8|PlanEndTime|计划结束时间|字符串|日期，YYYY/MM/DD hh:mm:ss|1|nan|nan|
|1.9|Sequence|执行顺序|字符串|整型|1|nan|卷包发生同一天内的切换，1开始<br>制丝班次内开始|
|1.10|Shift|班次|字符串|卷包，喂丝没有<br>1-早/2-中/3-晚|0..1|nan|nan|
|1.11|InputBatch|nan|nan|nan|0..n|nan|卷包：喂丝机 1<br>喂丝：成丝   0<br>成丝：叶丝   1..n<br>回用烟丝2:  0..n<br>叶丝：叶片   1<br>叶片：       0|
|1.11.1|InputPlanID|前工序计划号|字符串|nan|0..1|nan|当指定批次的物料不是通过计划进行生产的，比如回用烟丝二或者指定膨丝批次等|
|1.11.2|InputBatchCode|前工序批次号|字符串|nan|0..1|nan|指定批次号|
|1.11.3|Quantity|数量|字符串|卷包，喂丝没有|0..1|nan|nan|
|1.11.4|BatchSequence|批次顺序|字符串|卷包，喂丝没有|0..1|nan|nan|
|1.11.5|IsWholeBatch|是否整批|字符串|bool,false or true|0..1|nan|卷包，喂丝没有|
|1.11.6|IsMainChannel|是否走主通道|字符串|bool,false or true|0..1|1.0|nan|nan|
|1.11.7|IsDeleted|是否删除|字符串|bool,false or true|0..1|nan|用于喂丝机工单取消追加|
|1.11.8|IsLastOne|是否最后一个批次|字符串|bool,false or true|0..1|nan|只有喂丝才需要|
|1.11.9|MaterialCode|物料代码|字符串|nan|1|nan|nan|
|1.11.10|BOMRevision|版本号|字符串|nan|1|nan|nan|
|1.11.11|Tiled  |是否平铺|字符串|bool,false or true|0..1|nan|只有回用烟丝二才会<br>给出是否平铺|
|1.11.12|IsVaccum|是否真空回潮|字符串|bool,false or true|0..1|nan|叶片计划|
|1.11.13|IsSH93|是否走SH93|字符串|bool,false or true|0..1|nan|叶丝计划|
|1.11.14|IsHDT|是否走HDT|字符串|bool,false or true|0..1|nan|叶丝计划|
|1.11.15|IsFlavor|是否补香|字符串|bool,false or true|0..1|nan|叶丝计划|
|1.11.16|Unit|基本单位|字符串|...|

### 目标系统返回数据结构
|结构编号|名称|描述|字段类型|字段描述|occurrence|缺省值|
|----|----|----|----|----|----|----|
|1|Result|结果|字符串|枚举，1 - 成功，2 - 失败|1| |
|2|Reason|原因|字符串| | 0..1| |
|3|PlanID|计划 ID|字符串|H + 工单类型（2 位）+ 流水码（9 位，前补零），例：HHS000000001 杭州混丝工单；HS - 混丝，YP - 叶片，YS - 叶丝，WS - 喂丝，JB - 卷包|0..n| |
|4|ProductionLine|工序段|字符串|如果是制丝计划：一个制丝生产线(CP1)；如果是喂丝机计划：多个喂丝机代码(W1)；如果是卷包计划：一个机组(A1)|0..n| |
|5|ErrorCode|错误代码|字符串| | 0..1| |
|6|ErrorMessage|错误消息|字符串| | 0..1| |
| | | | | | | |
|填表说明：| | | | | | | |
|1. 结构编号：以树形结构编号方式，即第一层为 1，2，3…第二层为 1.1，1.2，2.1…。| | | | | | | |
|2. 名称：即字段的命名。| | | | | | | |
|3. 字段类型：integer、string、dateTime、boolean、float、bit、double、blob 等等。| | | | | | | |
|4. occurrence：1、1…unbounded、0..1、0..unbounded 等四种，（1：表示该节点有且只有一次，1…unbounded：表示该节点将循环出现一次以上，0..1：表示该节点可能不出现也有可能出现一次；0..unbounded：表示该节点可能不出现也有可能循环出现多次）。| | | | | | | |

### 发送数据结构映射关系
|源系统结构编号|源系统名称|目标系统结构编号|目标系统名称|
|----|----|----|----|
|1|WorkPlans| | |
|1.1|Plan|1|Plan|
|1.1.1|PlanID|1.1|PlanID|
|1.1.2|ProductionLine|1.2|ProductionLine|
|1.1.3|BatchCode|1.3|BatchCode|
|1.1.4|MaterialCode|1.4|MaterialCode|
|1.1.5|BOMRevision|1.5|BOMRevision|
|1.1.6|Quantity|1.6|Quantity|
|1.1.7|PlanStartTime|1.7|PlanStartTime|
|1.1.8|PlanEndTime|1.8|PlanEndTime|
|1.1.9|Sequence|1.9|Sequence|
|1.1.10|Shift|1.10|Shift|
|1.1.11|InputBatch|1.11|InputBatch|
|1.1.11.1.1|InputPlanID|1.11.1|InputPlanID|
|1.1.11.1.2|InputBatchCode|1.11.2|InputBatchCode|
|1.1.11.1.3|Quantity|1.11.3|Quantity|
|1.1.11.1.4|BatchSequence|1.11.4|BatchSequence|
|1.1.11.1.5|IsWholeBatch|1.11.5|IsWholeBatch|
|1.1.11.1.6|IsMainChannel|1.11.6|IsMainChannel|
|1.1.11.1.7|IsDeleted|1.11.7|IsDeleted|
|1.1.11.1.8|IsLastOne|1.11.8|IsLastOne|
|1.1.11.1.9|MaterialCode|1.11.9|MaterialCode|
|1.1.11.1.10|BOMRevision|1.11.1.10|BOMRevision|
|1.1.11.1.11|Tiled|1.11.1.11|Tiled|
|1.1.12|IsVaccum|1.1.12|IsVaccum|
|1.1.13|IsSH93|1.1.13|IsSH93|
|1.1.14|IsHDT|1.1.14|IsHDT|
|1.1.15|IsFlavor|1.1.15|IsFlavor|
|1.1.16|Unit|1.1.16|Unit|
|1.1.17|PlanDate|1.1.17|PlanDate|
|1.1.18|PlanOutputQuantity|1.1.18|PlanOutputQuantity|
|1.1.19|IsOutsourcing|1.1.19|IsOutsourcing|
|1.1.20|IsBackup|1.1.20|IsBackup|

### 返回数据结构映射关系
|源系统结构编号|源系统名称|目标系统结构编号|目标系统名称|
|----|----|----|----|
|1|Result|1|Result|
|2|Reason|2|Reason|
|3|PlanID|3|PlanID|
|4|ProductionLine|4|ProductionLine|
|5|ErrorCode|5|ErrorCode|
|6|ErrorMessage|6|ErrorMessage|