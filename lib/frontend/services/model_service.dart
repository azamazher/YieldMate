// ============================================================================
// MODEL SERVICE - TFLite model loading and inference
// ============================================================================
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';
import 'detection_service.dart';

class ModelService {
  /// Load model and labels from assets
  static Future<Map<String, dynamic>> loadModelAndLabels(
      BuildContext context) async {
    Interpreter? interpreter;
    List<String> labels = [];
    bool modelLoaded = false;

    try {
      // Try loading model with full asset path first
      try {
        print("📂 Attempting to load: assets/model.tflite");
        interpreter = await Interpreter.fromAsset('assets/model.tflite');
        print("✅ Model loaded successfully from assets/model.tflite");
      } catch (e, stackTrace) {
        print("⚠️ First attempt failed: $e");
        print("📋 Stack trace: $stackTrace");

        // Fallback: try without assets/ prefix
        try {
          print("📂 Trying alternative path: model.tflite");
          interpreter = await Interpreter.fromAsset('model.tflite');
          print("✅ Model loaded successfully from model.tflite");
        } catch (e2, stackTrace2) {
          print("❌ Both paths failed!");
          print("❌ Error 1: $e");
          print("❌ Error 2: $e2");
          print("❌ Stack trace 2: $stackTrace2");

          if (Platform.isMacOS) {
            print(
                "⚠️ macOS detected - tflite_flutter may have limited macOS support");
            print(
                "💡 Consider using Android/iOS for full TensorFlow Lite functionality");
          }

          rethrow;
        }
      }

      // Check if widget is still mounted before using context
      if (!context.mounted) {
        print("⚠️ Widget unmounted during model loading");
        return {
          'interpreter': null,
          'labels': [],
          'modelLoaded': false,
          'error': 'Widget unmounted',
        };
      }

      print("📝 Loading labels...");
      final labelData =
          await DefaultAssetBundle.of(context).loadString('assets/labels.txt');
      labels =
          labelData.split('\n').where((label) => label.isNotEmpty).toList();
      print("✅ Labels loaded successfully: ${labels.length} classes");
      print("📋 Labels: $labels");

      modelLoaded = true;

      return {
        'interpreter': interpreter,
        'labels': labels,
        'modelLoaded': modelLoaded,
        'error': null,
      };
    } catch (e, stackTrace) {
      print("❌ CRITICAL ERROR loading model or labels: $e");
      print("❌ Full stack trace: $stackTrace");
      print("❌ Platform: ${Platform.operatingSystem}");
      print("❌ OS Version: ${Platform.operatingSystemVersion}");

      String errorMessage = "Failed to load model";
      if (Platform.isMacOS) {
        errorMessage =
            "macOS: tflite_flutter may not fully support macOS. Try Android/iOS.";
      } else {
        errorMessage = "Error: ${e.toString()}";
      }

      return {
        'interpreter': null,
        'labels': [],
        'modelLoaded': false,
        'error': errorMessage,
      };
    }
  }

  /// Run model inference in isolate
  static Future<Map<String, dynamic>> runModelIsolate(
      Map<String, dynamic> params) async {
    final imagePath = params['imagePath'] as String;
    final modelBytes = params['modelBytes'] as Uint8List;
    final labels = params['labels'] as List<String>;
    final inputSize = params['inputSize'] as int;

    try {
      print("🔄 Loading model from bytes (${modelBytes.length} bytes)");
      final interpreter = Interpreter.fromBuffer(modelBytes);
      print("✅ Model loaded successfully");

      // Check model input/output shapes
      final inputTensors = interpreter.getInputTensors();
      final outputTensors = interpreter.getOutputTensors();
      print("📊 Input tensors: ${inputTensors.length}");
      for (var tensor in inputTensors) {
        print("   Input shape: ${tensor.shape}, type: ${tensor.type}");
      }
      print("📊 Output tensors: ${outputTensors.length}");
      for (var tensor in outputTensors) {
        print("   Output shape: ${tensor.shape}, type: ${tensor.type}");
      }

      // Load and process image
      print("🖼️ Loading image from: $imagePath");
      final imageFile = File(imagePath);
      if (!await imageFile.exists()) {
        throw Exception("Image file does not exist: $imagePath");
      }

      final imageBytes = await imageFile.readAsBytes();
      print("✅ Image loaded: ${imageBytes.length} bytes");

      final decodedImage = img.decodeImage(imageBytes);
      if (decodedImage == null) throw Exception("Cannot decode image");

      final imageWidth = decodedImage.width.toDouble();
      final imageHeight = decodedImage.height.toDouble();
      print("📐 Image dimensions: ${imageWidth}x${imageHeight}");

      // Get actual model input shape
      final inputShape = inputTensors[0].shape;
      print("🔄 Model expects input shape: $inputShape");

      final modelInputHeight = inputShape[1];
      final modelInputSize = modelInputHeight;

      print("📐 Model input size: ${modelInputSize}x${modelInputSize}");
      print("📐 Code parameter was: ${inputSize}x${inputSize}");

      // Resize image to match model's expected input size
      print(
          "🔄 Resizing image to ${modelInputSize}x${modelInputSize} (model's expected size)");
      final resized = img.copyResize(decodedImage,
          width: modelInputSize, height: modelInputSize);

      print("🔄 Converting to float array...");
      final floatBytes = Float32List(1 * modelInputSize * modelInputSize * 3);
      int bufferIndex = 0;
      for (var y = 0; y < modelInputSize; y++) {
        for (var x = 0; x < modelInputSize; x++) {
          final pixel = resized.getPixel(x, y);
          // Image package 4.x: Pixel object has r, g, b properties
          floatBytes[bufferIndex++] = pixel.r / 255.0;
          floatBytes[bufferIndex++] = pixel.g / 255.0;
          floatBytes[bufferIndex++] = pixel.b / 255.0;
        }
      }

      // Reshape to match model's expected input shape
      final input = floatBytes.reshape(inputShape);

      // Use actual model output shape
      final outputShape = outputTensors[0].shape;
      print("🔄 Creating output tensor with shape: $outputShape");
      final output = List.filled(outputShape.reduce((a, b) => a * b), 0.0)
          .reshape(outputShape);

      print("🚀 Running inference...");
      interpreter.run(input, output);
      print("✅ Inference completed");

      print("🔄 Processing output...");

      // Handle different output formats - convert dynamic to typed
      List<List<List<double>>> typedOutput;

      if (output is List<List<List<double>>>) {
        print(
            "   Output format: 3D List<double> (${output.length} x ${output[0].length} x ${output[0][0].length})");
        typedOutput = output;
      } else if (output is List<List<dynamic>>) {
        print(
            "   Output format: 2D List<dynamic> (${output.length} x ${output[0].length})");
        // Try to convert to typed
        if (output[0][0] is List) {
          typedOutput = output
              .map((row) => row
                  .map((val) =>
                      (val as List).map((v) => (v as num).toDouble()).toList())
                  .toList()
                  .cast<List<double>>())
              .toList()
              .cast<List<List<double>>>();
          print(
              "   Converted 3D dynamic to typed: ${typedOutput.length} x ${typedOutput[0].length} x ${typedOutput[0][0].length}");
        } else {
          typedOutput = [
            output
                .map((row) {
                  return row.map((val) => (val as num).toDouble()).toList();
                })
                .toList()
                .cast<List<double>>()
          ];
          print(
              "   Converted 2D dynamic to 3D typed: ${typedOutput.length} x ${typedOutput[0].length} x ${typedOutput[0][0].length}");
        }
      } else if (output is List<List<double>>) {
        print(
            "   Output format: 2D List<double> (${output.length} x ${output[0].length})");
        typedOutput = [output];
      } else {
        print("⚠️ Unknown output format: ${output.runtimeType}");
        throw Exception(
            "Unexpected output format. Expected List<List<List<double>>>, got ${output.runtimeType}");
      }

      interpreter.close();

      // Process output using DetectionService
      final recognitions = DetectionService.processOutput(
        typedOutput,
        labels,
        confThreshold: 0.5,
        iouThreshold: 0.45,
      );

      print("✅ Found ${recognitions.length} detections");

      return {
        'recognitions': recognitions,
        'imageWidth': imageWidth,
        'imageHeight': imageHeight,
      };
    } catch (e, stackTrace) {
      print("❌ Error in isolate: $e");
      print("❌ Stack trace: $stackTrace");
      rethrow;
    }
  }
}
