文档加载器开发笔记
========================

概述
----
本文档记录了文档加载器的开发过程和重要决策。

核心功能
~~~~~~~~
1. 统一加载接口
2. 多格式支持
3. 元数据提取
4. 错误处理

使用方法
--------
使用工厂模式获取加载器实例：

    from src.ai.core.loaders import DocumentLoaderFactory
    
    factory = DocumentLoaderFactory()
    doc = factory.load("path/to/file")

支持的格式
~~~~~~~~~~
- 文本类：TXT, MD, HTML, XML, JSON, RST
- 办公文档：PDF, DOCX, PPTX, XLSX, ODT
- 其他：EPUB, EML, MSG, 图片(OCR)

注意事项
--------
1. 确保文件存在且可读
2. 检查文件大小限制
3. 处理编码问题

.. note::
   这是一个 RST 格式的测试文件