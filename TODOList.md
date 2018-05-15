# TODO List

* 从左到右显示人的姓名
* KNN算法的利用
* 录入过程的优化

## 数据库设计

采用MySQL作为底层数据库,mysqlclient作为接口.

### 需要存储的东西

* Database: FDR

* Knowns Table: 认识的人, 具体包括:

  * Person_ID(UUID)
  * Name(VARCHAR(255))
  * Meet Position(TEXT)
  * Meet Time(TEXT)
  * LAST Meet TIME(DATETIME)
  * Newest Weibo(TEXT)

* Unknowns Table 不认识的人, 具体包括:

  * Person_ID(UUID)
  * First Meet Photo
  * First Meet Position
  * First Meet Time

* Vectors Table: 特征向量

  * Vector_ID
  * Vector(BLOB)
  * Person_ID(UUID)