// Backend service for online detection using Ultralytics server
import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart' show kIsWeb;

class BackendDetectionService {
  final String serverUrl;

  // Auto-detect the correct server URL based on platform
  // For Android: Try 10.0.2.2 (emulator) first, fallback to physical device IP
  // For iOS: Use localhost (works for simulator)
  // For physical devices: You may need to set your computer's IP manually
  static String get defaultServerUrl {
    if (kIsWeb) {
      return 'http://localhost:5000';
    } else if (Platform.isAndroid) {
      // Android emulator uses 10.0.2.2 to access host machine's localhost
      // For physical Android device, change this to your computer's IP:
      // return 'http://192.168.1.192:5000'; // Replace with your IP
      return 'http://10.0.2.2:5000';
    } else if (Platform.isIOS) {
      // iOS Simulator can use localhost
      // For physical iOS device, use your computer's IP:
      // return 'http://192.168.1.192:5000'; // Replace with your IP
      return 'http://localhost:5000';
    } else {
      // Desktop platforms
      return 'http://localhost:5000';
    }
  }

  BackendDetectionService({String? serverUrl})
      : serverUrl = serverUrl ?? defaultServerUrl;

  /// Detect fruits using backend server
  Future<List<Map<String, dynamic>>> detectFruits(File imageFile) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$serverUrl/detect'),
      );

      // Add image file
      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      // Send request with timeout
      var streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw Exception('Request timeout - server may be unreachable');
        },
      );

      var response = await http.Response.fromStream(streamedResponse);
      var responseData = jsonDecode(response.body);

      if (response.statusCode == 200 && responseData['success'] == true) {
        // Format detections for the app
        List<Map<String, dynamic>> detections = [];
        for (var det in responseData['detections']) {
          final bbox = det['bbox'] as List;
          detections.add({
            'detectedClass': det['class'] as String,
            'confidenceInClass': (det['confidence'] as num).toDouble(),
            'rect': Rect.fromLTRB(
              (bbox[0] as num).toDouble(), // x1
              (bbox[1] as num).toDouble(), // y1
              (bbox[2] as num).toDouble(), // x2
              (bbox[3] as num).toDouble(), // y2
            ),
          });
        }
        return detections;
      } else {
        throw Exception(responseData['error'] ?? 'Unknown error from server');
      }
    } catch (e) {
      print('❌ Backend detection error: $e');
      rethrow;
    }
  }

  /// Check if server is reachable
  Future<bool> checkHealth() async {
    try {
      print('🔍 Checking server health at: $serverUrl/health');
      var response = await http
          .get(Uri.parse('$serverUrl/health'))
          .timeout(
            const Duration(seconds: 10),
            onTimeout: () {
              print('⏱️ Health check timeout - server may be unreachable');
              throw Exception('Connection timeout');
            },
          );
      
      print('📊 Health check response: ${response.statusCode}');
      print('📄 Response body: ${response.body}');
      
      if (response.statusCode == 200) {
        print('✅ Server is healthy');
        return true;
      } else {
        print('❌ Server returned status: ${response.statusCode}');
        return false;
      }
    } on SocketException catch (e) {
      print('❌ Network error: ${e.message}');
      print('💡 Make sure:');
      print('   1. Backend server is running');
      print('   2. Server URL is correct: $serverUrl');
      print('   3. Device/emulator can reach the server');
      return false;
    } on HttpException catch (e) {
      print('❌ HTTP error: ${e.message}');
      return false;
    } catch (e) {
      print('❌ Server health check failed: $e');
      print('💡 Server URL: $serverUrl');
      print('💡 Make sure the backend server is running');
      return false;
    }
  }
}
