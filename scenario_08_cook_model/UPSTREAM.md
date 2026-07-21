# 上游固定点

- `hzyhhzy/UmaAi@2b06fb9` (`Cook2`)
  - `UmaSimulator/Game/Game.cpp`: 回合、目标赛、料理、收获、固定事件和统计随机事件。
  - `UmaSimulator/NeuralNet/NNInput.cpp`: 上游输入编码。
  - `UmaSimulator/NeuralNet/TrainingSample.cpp`: 搜索值经 softmax 生成 policy 标签。
  - `training/model.py`, `training/export_onnx.py`: 模型与 ONNX 导出参考。
- `xulai1001/UmaSimulator@feac640` (`cook`)
  - `Scripts/export_uma/uma/101101-grass-wonder.json`: 固定草上飞配置。

重要边界：Cook2 的 `checkRandomEvents` 明确是统计模拟，并不包含逐条草上飞专属事件文本/选择。因此重建代码不得把 generic event approximation 描述成完整角色事件数据库。
