#include <onnx/onnx_pb.h>

int main() {
    onnx::ModelProto model;
    model.set_ir_version(onnx::IR_VERSION);
    return model.ir_version() == onnx::IR_VERSION ? 0 : 1;
}
