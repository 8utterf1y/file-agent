```markdown
# Java 字符串常量池与 `==` / `equals()` 完全指南

> 本文基于 JLS (Java语言规范) / JVMS (Java虚拟机规范) / Oracle API 文档。

## 核心问题速查表

| 问题 | 答案 |
|------|------|
| `==` 到底比较什么？ | **引用地址**。只有两个引用指向同一个对象时才返回 `true`。 |
| `equals()` 到底比较什么？ | `String` 重写后比较**字符序列内容**。`Object` 默认等同于 `==`。 |
| `"abc"` 放在哪里？ | **字符串池 (String Pool)**。 |
| `new String("abc")` 放在哪里？ | **Java 堆内存**。同时会引用字符串池中的 `"abc"`。 |
| `"a" + "b"` 和 `a + b` 为什么不一样？ | 前者是**编译期常量**，直接折叠为 `"ab"`；后者是**运行期拼接**，生成新对象。 |
| `intern()` 到底做了什么？ | 返回字符串池中的规范对象。池中没有时，将当前对象加入池中并返回。 |
| 面试题里"创建几个对象"应该怎么严谨分析？ | 使用**五步分析法**，不能脱离"字符串池中是否已存在"这个前提。 |


## 一、先建立正确模型：不要一上来背"几个对象"

很多文章会直接说：

```java
String s = new String("abc"); // 创建 2 个对象
```

这个说法在很多场景下可以帮助入门，但如果继续遇到：

```java
String s = new String("a" + "b");
String s = new String("ab") + "ab";
String s = new String("a") + new String("b");
s.intern();
```

就很容易混乱。

**更稳定的分析方式**：


| 步骤   | 判断内容                                   |
| ------ | ------------------------------------------ |
| 第一步 | 看是不是**字符串字面量**                   |
| 第二步 | 看是不是**`new String(...)`**              |
| 第三步 | 看**`+`** 是编译期拼接还是运行期拼接       |
| 第四步 | 看有没有调用**`intern()`**                 |
| 第五步 | 看字符串池中**之前是否已经有同内容字符串** |

这 **5 步**比死背"几个对象"可靠得多。

## 二、先分清三个概念

> 很多中文文章把这几个词混着叫"常量池"，这是混乱的根源。

### 1. class 文件常量池 (Constant Pool)

`.class` 文件里有一个 `constant_pool` 表，记录类名、方法名、字段名、**字符串字面量**等符号信息。

JVMS 规定：字符串字面量会从 class 文件中的 `CONSTANT_String_info` 结构派生。

### 2. 运行时常量池 (Runtime Constant Pool)

类被 JVM 加载后，class 文件常量池中的内容会进入运行时结构。属于 JVM 运行时数据区的一部分。

### 3. 字符串池 / String Pool / StringTable

维护的是**共享的 String 对象引用**。

JLS 规定：**字符串字面量总是指向同一个 String 实例**。

```java
String a = "abc";
String b = "abc";
System.out.println(a == b); // true
```

## 三、字符串池的位置：JDK 6 → 7 → 8 的变化


| JDK 版本     | 字符串池位置       | 重点                                                     |
| ------------ | ------------------ | -------------------------------------------------------- |
| JDK 6 及以前 | 永久代 (PermGen)   | `intern()` 行为与 JDK 7+ 有差异                          |
| JDK 7        | **Java 堆** (Heap) | interned strings 移到了堆中                              |
| JDK 8+       | **Java 堆** (Heap) | 永久代移除，使用 Metaspace，但 interned strings 仍在堆中 |

**影响**：JDK 7+ 中，如果池中没有某个字符串，而堆中已有相同内容的 String 对象，`intern()` 可以让池**记录这个堆对象的引用**，而不是复制一个新对象。

## 四、`==` 和 `equals()` 的本质区别

### 1. `==`：比较引用地址

```java
String a = new String("abc");
String b = new String("abc");
System.out.println(a == b); // false
```

JLS：两个引用都为 `null`，或指向**同一个对象**时，`==` 才返回 `true`。

### 2. `equals()`：String 重写后比较内容

```java
String a = new String("abc");
String b = new String("abc");
System.out.println(a.equals(b)); // true
```

Oracle API 文档：`String.equals()` 在参数非 null，且表示**相同字符序列**时返回 `true`。

### 3. `Object.equals()` 默认就是 `==`

```java
class User { String name; }

User u1 = new User();
User u2 = new User();
System.out.println(u1.equals(u2)); // false，未重写 equals()
```

### 4. 实际开发推荐写法

```java
// 推荐：str 为 null 时不会空指针
if ("abc".equals(str)) { }

// 不推荐：str 可能为 null
if (str.equals("abc")) { }

// 推荐：null 安全
if (Objects.equals(str1, str2)) { }
```

## 五、`String s = "abc"` 的过程

```java
String s1 = "abc";
String s2 = "abc";
System.out.println(s1 == s2); // true
```

**流程**：

1. 字符串池中有没有 `"abc"`？
   - 没有 → 创建并放入池中
   - 有 → 直接复用池中的对象

JLS 示例：同一个包、不同类、甚至不同包中的**相同字符串字面量**，都表示对同一个 String 对象的引用。

## 六、`String s = new String("abc")` 的过程

```java
String s1 = "abc";
String s2 = new String("abc");

System.out.println(s1 == s2);      // false
System.out.println(s1.equals(s2)); // true
```

**分解**：


| 变量 | 指向                          |
| ---- | ----------------------------- |
| `s1` | 字符串池中的`"abc"`           |
| `s2` | 堆上 new 出来的新 String 对象 |

**"创建几个对象"才严谨？**

```java
String s = new String("abc");
```


| 前提                 | 涉及对象                               |
| -------------------- | -------------------------------------- |
| 池中**没有** `"abc"` | 池中`"abc"` + 堆上 `new String("abc")` |
| 池中**已有** `"abc"` | 只新增堆上`new String("abc")`          |

> **关键**：不能脱离"字符串池中是否已经存在"来谈创建对象个数。

## 七、编译期拼接：`"a" + "b"`

```java
String s1 = "a" + "b";
String s2 = "ab";
System.out.println(s1 == s2); // true
```

**原因**：两边都是字符串字面量，是**编译期常量表达式**，编译器直接折叠为 `"ab"`。

JLS：`String` 类型的常量表达式总是 `intern`，共享唯一实例。

**⚠️ 重要纠错**：

```java
String s = new String("a" + "b");
```

有人说池中会有 `"a"`、`"b"`、`"ab"` 三个对象——**不严谨**。

因为 `"a" + "b"` 是编译期常量，直接折叠为 `"ab"`。更合理的分析是：

```java
String s = new String("ab");
```

重点是：池中有 `"ab"`，堆上 new 出一个新对象。

## 八、运行期拼接：变量参与 `+`

```java
String a = "a";
String b = "b";
String s1 = a + b;
String s2 = "ab";

System.out.println(s1 == s2);      // false
System.out.println(s1.equals(s2)); // true
```

**关键区别**：`a` 和 `b` 是**普通局部变量**，编译期无法确定值，因此是**运行期拼接**。


| 变量 | 指向                             |
| ---- | -------------------------------- |
| `a`  | 池中的`"a"`                      |
| `b`  | 池中的`"b"`                      |
| `s1` | 运行期拼接出的**新 String 对象** |
| `s2` | 池中的`"ab"`                     |

## 九、`final` 变量参与拼接：要看是不是"常量变量"

### ✅ 编译期常量（`true`）

```java
final String a = "a";
final String b = "b";
String s1 = a + b;
String s2 = "ab";
System.out.println(s1 == s2); // true
```

因为 `a` 和 `b` 是 **`final` + 编译期可确定的初始化值**，属于**常量变量**，编译器直接折叠。

### ❌ 不是编译期常量（`false`）

```java
static String getA() { return "a"; }

final String a = getA();
final String b = "b";
String s1 = a + b;
String s2 = "ab";
System.out.println(s1 == s2); // false
```

虽然 `a` 是 `final`，但值来自方法调用，编译期无法确定，所以是运行期拼接。

> **结论**：`final` 不等于一定是编译期常量。只有 **`final` + 编译期可确定的初始化值** 才是常量变量。

## 十、字符串拼接底层一定是 `StringBuilder` 吗？

**不一定。**

Java 8 及以前，通常编译成：

```java
new StringBuilder().append(a).append(b).toString();
```

但从 Java 9+ 开始，引入了 **`StringConcatFactory`**，使用 `invokedynamic` 实现更高效的拼接。

> **学习时不要死记**："运行期拼接 = 一定 new StringBuilder"
>
> **应该记**："运行期拼接 = 语义上产生新的 String 结果；具体实现由编译器和 JDK 决定。"

## 十一、`intern()` 到底做什么？

Oracle Java 8 API 文档：

> 调用 `intern()` 时，如果池中已经包含一个通过 `equals()` 判断相等的字符串，就返回池中的那个字符串；否则，把当前 String 对象加入池中，并返回当前对象的引用。

**关键特性**：对任意字符串 `s` 和 `t`，`s.intern() == t.intern()` 为 `true` **当且仅当** `s.equals(t)` 为 `true`。

```java
String s1 = new String("abc");
String s2 = s1.intern();
String s3 = "abc";

System.out.println(s1 == s2); // false
System.out.println(s2 == s3); // true
```

## 十二、`intern()` 经典题：为什么有时 `true`，有时 `false`？

### 情况 1：池中已经有目标字符串

```java
String s1 = new String("ab");
String s2 = s1.intern();
String s3 = "ab";

System.out.println(s1 == s2); // false
System.out.println(s2 == s3); // true
```

**原因**：`new String("ab")` 中直接出现了 `"ab"` 字面量，池中已有 `"ab"`，所以 `intern()` 返回池中的对象。

### 情况 2：运行期拼接，池中之前没有（JDK 7+）

```java
public class Demo {
    public static void main(String[] args) {
        String s1 = new String("a") + new String("b");
        String s2 = s1.intern();
        String s3 = "ab";

        System.out.println(s1 == s2); // true
        System.out.println(s1 == s3); // true
    }
}
```

**原因**：

1. `s1` 是运行期拼接出的新 `"ab"` 对象，池中**没有** `"ab"`。
2. `s1.intern()` 将堆上的 `s1` 对象记录到池中。
3. `"ab"` 字面量从池中获取，正好是 `s1` 指向的对象。

### 情况 3：为什么你自己跑可能是 `false`？

如果你把很多例子放在同一个 `main` 方法里，前面已经执行过：

```java
String x = "ab"; // 池中已经有 "ab" 了
```

然后再执行：

```java
String s1 = new String("a") + new String("b");
String s2 = s1.intern();
System.out.println(s1 == s2); // false
```

> **结论**：`intern()` 题的关键是——**调用 `intern()` 时，池中是否已经有同内容字符串？**

## 十三、逐个分析常见代码

> 以下分析默认：讨论的是 **String 对象本身**，不把底层 `byte[]/char[]`、拼接辅助对象、JIT 优化临时对象算进去。

### 例 1：字面量赋值

```java
String s1 = "abc";
String s2 = "abc";
System.out.println(s1 == s2); // true
```


| 变量 | 指向          |
| ---- | ------------- |
| `s1` | 池中的`"abc"` |
| `s2` | 池中的`"abc"` |

### 例 2：`new String("abc")`

```java
String s1 = "abc";
String s2 = new String("abc");
System.out.println(s1 == s2);      // false
System.out.println(s1.equals(s2)); // true
```


| 变量 | 指向                    |
| ---- | ----------------------- |
| `s1` | 池中的`"abc"`           |
| `s2` | 堆上的新`String("abc")` |

**对象数量**：

- 池中没有 `"abc"`：池中 `"abc"` + 堆中 `new String("abc")`
- 池中已有 `"abc"`：只新增堆中 `new String("abc")`

### 例 3：两个 `new String("abc")`

```java
String s1 = new String("abc");
String s2 = new String("abc");
System.out.println(s1 == s2);      // false
System.out.println(s1.equals(s2)); // true
```


| 变量 | 指向                 |
| ---- | -------------------- |
| `s1` | 堆对象 A             |
| `s2` | 堆对象 B（不同于 A） |

### 例 4：`"a" + "b"`

```java
String s1 = "a" + "b";
String s2 = "ab";
System.out.println(s1 == s2); // true
```

**原因**：编译期常量表达式，直接折叠为 `"ab"`。

### 例 5：`new String("a" + "b")`

```java
String s1 = new String("a" + "b");
String s2 = "ab";
System.out.println(s1 == s2);      // false
System.out.println(s1.equals(s2)); // true
```

**实际等价于**：`new String("ab")`，因为 `"a" + "b"` 编译期折叠为 `"ab"`。

### 例 6：普通变量拼接

```java
String a = "a";
String b = "b";
String s1 = a + b;
String s2 = "ab";
System.out.println(s1 == s2);      // false
System.out.println(s1.equals(s2)); // true
```


| 变量 | 指向                                |
| ---- | ----------------------------------- |
| `a`  | 池中的`"a"`                         |
| `b`  | 池中的`"b"`                         |
| `s1` | 运行期拼接出的**新** `String("ab")` |
| `s2` | 池中的`"ab"`                        |

### 例 7：`final` 常量变量拼接

```java
final String a = "a";
final String b = "b";
String s1 = a + b;
String s2 = "ab";
System.out.println(s1 == s2); // true
```

**原因**：编译期可确定的常量变量，直接折叠。

### 例 8：`final` 但不是编译期常量

```java
static String getA() { return "a"; }

public static void main(String[] args) {
    final String a = getA();
    final String b = "b";
    String s1 = a + b;
    String s2 = "ab";
    System.out.println(s1 == s2); // false
}
```

**原因**：`a` 的值来自方法调用，编译期无法确定，运行期拼接。

### 例 9：`new String("ab") + "ab"`

```java
String s = new String("ab") + "ab";
String t = "abab";

System.out.println(s == t);      // false
System.out.println(s.equals(t)); // true
```

**分析**：

1. `new String("ab")` → 堆对象 A
2. `A + "ab"` → 运行期拼接 → 堆对象 C（`"abab"`）
3. `t` → 池中的 `"abab"`

### 例 10：`new String("ab") + new String("ab")`

```java
String s = new String("ab") + new String("ab");
String t = "abab";

System.out.println(s == t);      // false
System.out.println(s.equals(t)); // true
```

**涉及对象**：

1. 池中的 `"ab"`
2. 堆对象 A（第一个 `new String("ab")`）
3. 堆对象 B（第二个 `new String("ab")`）
4. 堆对象 C（运行期拼接结果 `"abab"`）
5. 池中的 `"abab"`（`t` 指向）

### 例 11：普通变量拼接后 `intern()`

```java
String a = "a";
String b = "b";
String s1 = a + b;
String s2 = s1.intern();
String s3 = "ab";

System.out.println(s1 == s2);
System.out.println(s2 == s3);
```

**结果取决于池中是否有 `"ab"`**：


| 调用`intern()` 前池中 | `s1 == s2` | `s2 == s3` |
| --------------------- | ---------- | ---------- |
| 已有`"ab"`            | `false`    | `true`     |
| 没有`"ab"` (JDK 7+)   | `true`     | `true`     |

## 十四、常见情况汇总表


| 代码片段                                             | 是否编译期常量 | `==` 典型结果 | 原因                          |
| ---------------------------------------------------- | -------------- | ------------- | ----------------------------- |
| `"abc" == "abc"`                                     | 是             | `true`        | 两个字面量指向池中同一对象    |
| `new String("abc") == "abc"`                         | 否             | `false`       | 堆中新对象 vs 池对象          |
| `new String("abc").equals("abc")`                    | 否             | `true`        | 内容相同                      |
| `"a" + "b" == "ab"`                                  | 是             | `true`        | 编译期折叠为`"ab"`            |
| `String a="a"; String b="b"; a+b == "ab"`            | 否             | `false`       | 变量参与，运行期拼接          |
| `final String a="a"; final b="b"; a+b == "ab"`       | 是             | `true`        | 常量变量，编译期折叠          |
| `final String a=getA(); a+"b" == "ab"`               | 否             | `false`       | `getA()` 不是编译期常量       |
| `(new String("a")+new String("b")).equals("ab")`     | 否             | `true`        | 内容相同                      |
| `(new String("a")+new String("b")) == "ab"`          | 否             | 通常`false`   | 运行期拼接结果不是池对象      |
| `(new String("a")+new String("b")).intern() == "ab"` | —             | 可能`true`    | `intern()` 返回池中的规范对象 |

## 十五、完整判断流程

### 第 1 步：看到 `==`，翻译成"是不是同一个对象"

```java
s1 == s2
```

不要翻译成"内容是否相等"，要翻译成"**s1 和 s2 是否指向同一个 String 对象**"。

内容相等用：`s1.equals(s2)`

### 第 2 步：看到字面量，想到字符串池

```java
"abc"
```

它来自字符串池，相同内容的字符串字面量**共享同一个对象**。

### 第 3 步：看到 `new String(...)`，想到堆中新对象

```java
new String("abc")
```

一定会产生一个**不同于池中字面量对象**的新 String 对象。

### 第 4 步：看到 `+`，判断编译期还是运行期


| 编译期（折叠）                               | 运行期（新对象）                        |
| -------------------------------------------- | --------------------------------------- |
| `"a" + "b"`                                  | `String a = "a"; String b = "b"; a + b` |
| `final String a = "a"; final b = "b"; a + b` | `final String a = getA(); a + "b"`      |

### 第 5 步：看到 `intern()`，问池中有没有

判断标准：**调用 `intern()` 那一刻，池中是否已有 `equals` 相等的字符串？**


| 情况     | 行为                               |
| -------- | ---------------------------------- |
| 池中已有 | 返回池中已有对象                   |
| 池中没有 | 把当前对象关联到池中，返回当前对象 |

## 十六、最容易错的三句话

### ❌ 错误 1：`final` 拼接一定是编译期拼接

```java
final String a = getA();
String s = a + "b"; // 这不是编译期常量
```

必须是 **`final` + 编译期可确定的值**：

```java
final String a = "a"; // 这才是编译期常量
```

### ❌ 错误 2：`new String("a" + "b")` 一定创建 `"a"`、`"b"`、`"ab"` 三个池对象

不严谨。`"a" + "b"` 是编译期常量，直接折叠为 `"ab"`，更合理地按 `new String("ab")` 分析。

### ❌ 错误 3：`intern()` 后一定和字面量 `==`

```java
String s = new String("ab");
String i = s.intern();
System.out.println(s == i); // false（因为池中已有 "ab"）
```

但如果是这样：

```java
String s = new String("a") + new String("b");
String i = s.intern();
String t = "ab";
System.out.println(s == i); // JDK 7+ 干净环境下通常 true
System.out.println(s == t); // JDK 7+ 干净环境下通常 true
```

## 十七、最终记忆版

### 一句话总结

> 字面量进池，new 在堆；
> `==` 看地址，`equals` 看内容；
> 字面量 `+` 字面量在编译期合并；
> 变量 `+` 变量在运行期产生新字符串；
> `intern` 返回池中的规范对象，池中没有时才把当前对象放进去。

### 判断口诀

```
先看 == 还是 equals；
再看 literal 还是 new；
再看 + 是编译期还是运行期；
最后看 intern 调用前池里有没有。
```

掌握这套流程后，绝大多数字符串常量池、`equals()`、`==`、`intern()` 的题都能自己推出来，不需要死背答案。

```

```

