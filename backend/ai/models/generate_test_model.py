"""
Generate a minimal test ONNX model for vehicle classification.

Input:  float32 [1, 3, 224, 224]
Output: float32 [1, 4]  (logits for three_wheeler, motorcycle, four_wheeler, unknown)

Architecture: GlobalAveragePool -> Flatten -> Gemm (FC with bias)
Always predicts three_wheeler (index 0) as the highest-logit class.
"""

import numpy as np
import onnx
from onnx import helper, numpy_helper

TARGET_PATH = __file__.replace("generate_test_model.py", "vehicle_classifier.onnx")


def _make_graph():
    input_tvi = helper.make_tensor_value_info(
        "input", onnx.TensorProto.FLOAT, [1, 3, 224, 224]
    )
    output_tvi = helper.make_tensor_value_info(
        "output", onnx.TensorProto.FLOAT, [1, 4]
    )

    pool_node = helper.make_node(
        "GlobalAveragePool",
        inputs=["input"],
        outputs=["pooled"],
        name="GlobalAvgPool",
    )

    flatten_node = helper.make_node(
        "Flatten",
        inputs=["pooled"],
        outputs=["flattened"],
        axis=1,
        name="Flatten",
    )

    W = np.zeros((3, 4), dtype=np.float32)
    np.fill_diagonal(W, 1.0)
    B = np.array([2.0, 0.3, 0.2, 0.1], dtype=np.float32)

    W_init = numpy_helper.from_array(W, name="fc_weight")
    B_init = numpy_helper.from_array(B, name="fc_bias")

    gemm_node = helper.make_node(
        "Gemm",
        inputs=["flattened", "fc_weight", "fc_bias"],
        outputs=["output"],
        alpha=1.0,
        beta=1.0,
        transA=0,
        transB=0,
        name="FC",
    )

    graph = helper.make_graph(
        nodes=[pool_node, flatten_node, gemm_node],
        name="VehicleClassifier",
        inputs=[input_tvi],
        outputs=[output_tvi],
        initializer=[W_init, B_init],
    )
    return graph


def generate():
    graph = _make_graph()
    model = helper.make_model(graph, producer_name="RetroMindAI", ir_version=9)
    model.opset_import[0].version = 17
    onnx.checker.check_model(model)
    onnx.save(model, TARGET_PATH)
    print(f"Test ONNX model saved to {TARGET_PATH}")
    print(f"  Input:  {model.graph.input[0].type.tensor_type}")
    print(f"  Output: {model.graph.output[0].type.tensor_type}")


if __name__ == "__main__":
    generate()
