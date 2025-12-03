// ============================================================================
// LIVE DETECTION PAGE - Real-time fruit detection with tracking and counting
// ============================================================================
import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../services/backend_service.dart';

// Tracked fruit model
class TrackedFruit {
  final int id;
  final String className;
  final List<dynamic> bbox;
  final Rect rect;
  final double confidence;
  final int framesSeen;

  TrackedFruit({
    required this.id,
    required this.className,
    required this.bbox,
    required this.rect,
    required this.confidence,
    required this.framesSeen,
  });
}

class LiveDetectionPage extends StatefulWidget {
  const LiveDetectionPage({super.key});

  @override
  State<LiveDetectionPage> createState() => _LiveDetectionPageState();
}

class _LiveDetectionPageState extends State<LiveDetectionPage> {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isInitialized = false;
  bool _isDetecting = false;
  bool _isPaused = false;
  
  Map<int, TrackedFruit> _trackedFruits = {};
  int _totalCount = 0;
  int _activeObjects = 0;
  
  Timer? _detectionTimer;
  final BackendDetectionService _backendService = BackendDetectionService();
  
  // Image dimensions from last detection
  double _imageWidth = 640.0;
  double _imageHeight = 480.0;
  
  // Error handling
  String? _errorMessage;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras == null || _cameras!.isEmpty) {
        setState(() {
          _hasError = true;
          _errorMessage = 'No cameras available';
        });
        return;
      }

      _controller = CameraController(
        _cameras![0],
        ResolutionPreset.medium, // Use medium for better performance
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );

      await _controller!.initialize();

      if (!mounted) return;

      setState(() {
        _isInitialized = true;
      });

      // Check server health before starting detection
      final isHealthy = await _backendService.checkHealth();
      if (!isHealthy) {
        setState(() {
          _hasError = true;
          _errorMessage = 'Cannot connect to detection server. Please ensure the server is running.';
        });
        return;
      }

      // Start continuous detection
      _startDetection();
    } catch (e) {
      setState(() {
        _hasError = true;
        _errorMessage = 'Camera initialization failed: $e';
      });
    }
  }

  void _startDetection() {
    if (_isPaused) return;
    
    _detectionTimer = Timer.periodic(const Duration(milliseconds: 300), (timer) async {
      if (!_isDetecting && !_isPaused && _controller != null && _controller!.value.isInitialized) {
        await _detectFruits();
      }
    });
  }

  void _stopDetection() {
    _detectionTimer?.cancel();
    _detectionTimer = null;
  }

  Future<void> _detectFruits() async {
    if (!mounted || _controller == null || !_controller!.value.isInitialized) return;
    if (_isDetecting || _isPaused) return;

    setState(() {
      _isDetecting = true;
      _hasError = false;
      _errorMessage = null;
    });

    try {
      // Take picture
      final image = await _controller!.takePicture();
      
      // Send to server for detection with tracking
      final result = await _backendService.detectFruitsLive(File(image.path));

      if (!mounted) return;

      setState(() {
        _totalCount = result['total_count'] ?? 0;
        _activeObjects = result['active_objects'] ?? 0;

        // Update tracked fruits
        final trackedList = result['tracked_objects'] as List;
        _trackedFruits = {};

        for (var obj in trackedList) {
          final id = obj['id'] as int;
          final bbox = obj['bbox'] as List;
          
          // Update image dimensions from bbox if available
          if (bbox.length >= 4) {
            _imageWidth = (bbox[2] as num).toDouble(); // x2
            _imageHeight = (bbox[3] as num).toDouble(); // y2
          }
          
          _trackedFruits[id] = TrackedFruit(
            id: id,
            className: obj['class'],
            bbox: bbox,
            rect: obj['rect'],
            confidence: obj['confidence'],
            framesSeen: obj['frames_seen'],
          );
        }
      });

      // Delete temporary image file
      await File(image.path).delete();
    } catch (e) {
      if (!mounted) return;
      
      setState(() {
        _hasError = true;
        _errorMessage = 'Detection error: ${e.toString()}';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isDetecting = false;
        });
      }
    }
  }

  Future<void> _resetTracker() async {
    final success = await _backendService.resetTracker();
    if (success) {
      setState(() {
        _trackedFruits = {};
        _totalCount = 0;
        _activeObjects = 0;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Counter reset successfully'),
            duration: Duration(seconds: 2),
            backgroundColor: Colors.green,
          ),
        );
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to reset counter'),
            duration: Duration(seconds: 2),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _togglePause() {
    setState(() {
      _isPaused = !_isPaused;
    });
    
    if (_isPaused) {
      _stopDetection();
    } else {
      _startDetection();
    }
  }

  Future<void> _showServerInfo() async {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    bool isHealthy = false;
    Map<String, dynamic>? trackerStatus;

    // Check server health
    try {
      isHealthy = await _backendService.checkHealth();
      
      // Try to get tracker status
      try {
        final response = await http.get(
          Uri.parse('${_backendService.serverUrl}/tracker_status'),
        ).timeout(const Duration(seconds: 3));
        
        if (response.statusCode == 200) {
          trackerStatus = jsonDecode(response.body);
        }
      } catch (e) {
        // Ignore tracker status errors
      }
    } catch (e) {
      // Health check failed
    }

    if (!mounted) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: isDark ? const Color(0xFF2A2A2A) : Colors.white,
        title: Row(
          children: [
            Icon(
              Icons.info_outline,
              color: Colors.blue,
              size: 28,
            ),
            const SizedBox(width: 12),
            const Text(
              'Server Details',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildInfoRow(
                context,
                'Server URL:',
                _backendService.serverUrl,
                isDark: isDark,
              ),
              const SizedBox(height: 16),
              _buildInfoRow(
                context,
                'Connection:',
                isHealthy ? 'Connected ✅' : 'Disconnected ❌',
                isDark: isDark,
                valueColor: isHealthy ? Colors.green : Colors.red,
              ),
              const SizedBox(height: 16),
              Divider(
                color: isDark ? Colors.grey[700] : Colors.grey[300],
              ),
              const SizedBox(height: 16),
              _buildInfoRow(
                context,
                'Total Fruits:',
                '$_totalCount',
                isDark: isDark,
                valueColor: Colors.orange,
              ),
              const SizedBox(height: 12),
              _buildInfoRow(
                context,
                'Active Objects:',
                '$_activeObjects',
                isDark: isDark,
              ),
              if (trackerStatus != null) ...[
                const SizedBox(height: 12),
                _buildInfoRow(
                  context,
                  'Tracker Status:',
                  'Active',
                  isDark: isDark,
                  valueColor: Colors.green,
                ),
              ],
              const SizedBox(height: 16),
              Divider(
                color: isDark ? Colors.grey[700] : Colors.grey[300],
              ),
              const SizedBox(height: 16),
              Text(
                'Detection Status:',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: isDark ? Colors.grey[300] : Colors.grey[700],
                ),
              ),
              const SizedBox(height: 8),
              _buildInfoRow(
                context,
                'Camera:',
                _isInitialized ? 'Initialized ✅' : 'Not Initialized ❌',
                isDark: isDark,
                valueColor: _isInitialized ? Colors.green : Colors.red,
              ),
              const SizedBox(height: 8),
              _buildInfoRow(
                context,
                'Detection:',
                _isPaused
                    ? 'Paused ⏸️'
                    : _isDetecting
                        ? 'Detecting... 🔄'
                        : 'Active ✅',
                isDark: isDark,
                valueColor: _isPaused
                    ? Colors.orange
                    : _isDetecting
                        ? Colors.blue
                        : Colors.green,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
          if (isHealthy)
            TextButton.icon(
              onPressed: () {
                Navigator.pop(context);
                _resetTracker();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Reset Counter'),
            ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(
    BuildContext context,
    String label,
    String value, {
    bool isDark = false,
    Color? valueColor,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 14,
                color: isDark ? Colors.grey[400] : Colors.grey[700],
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 14,
                color: valueColor ?? (isDark ? Colors.white : Colors.black87),
                fontFamily: 'monospace',
                fontWeight: valueColor != null ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _stopDetection();
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Live Detection'),
        centerTitle: true,
        actions: [
          // Server Info button
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: _showServerInfo,
            tooltip: 'Server Info',
          ),
          // Reset button
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _resetTracker,
            tooltip: 'Reset Counter',
          ),
          // Pause/Resume button
          IconButton(
            icon: Icon(_isPaused ? Icons.play_arrow : Icons.pause),
            onPressed: _togglePause,
            tooltip: _isPaused ? 'Resume Detection' : 'Pause Detection',
          ),
        ],
      ),
      body: _hasError && !_isInitialized
          ? _buildErrorScreen(isDark)
          : !_isInitialized
              ? _buildLoadingScreen(isDark)
              : _buildCameraView(isDark),
    );
  }

  Widget _buildLoadingScreen(bool isDark) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(
              Theme.of(context).primaryColor,
            ),
          ),
          const SizedBox(height: 24),
          Text(
            _errorMessage ?? 'Initializing camera...',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              color: isDark ? Colors.grey[400] : Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorScreen(bool isDark) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            const SizedBox(height: 24),
            Text(
              'Error',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : Colors.black87,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              _errorMessage ?? 'Unknown error occurred',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16,
                color: isDark ? Colors.grey[400] : Colors.grey[600],
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: () {
                setState(() {
                  _hasError = false;
                  _errorMessage = null;
                });
                _initializeCamera();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraView(bool isDark) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return _buildLoadingScreen(isDark);
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        // Camera preview
        SizedBox.expand(
          child: CameraPreview(_controller!),
        ),

        // Error overlay
        if (_hasError && _errorMessage != null)
          Positioned(
            top: 16,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(0.9),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error, color: Colors.white, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

        // Bounding boxes overlay
        CustomPaint(
          painter: LiveDetectionPainter(
            trackedFruits: _trackedFruits.values.toList(),
            imageWidth: _imageWidth,
            imageHeight: _imageHeight,
          ),
          child: Container(),
        ),

        // Count display overlay
        Positioned(
          top: 16,
          left: 16,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(0.7),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: Colors.green,
                width: 2,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.local_fire_department,
                      color: Colors.orange,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Total Fruits',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '$_totalCount',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (_activeObjects > 0)
                  Text(
                    '$_activeObjects active',
                    style: TextStyle(
                      color: Colors.green[300],
                      fontSize: 10,
                    ),
                  ),
              ],
            ),
          ),
        ),

        // Status indicator
        Positioned(
          top: 16,
          right: 16,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: _isPaused
                  ? Colors.orange.withOpacity(0.8)
                  : _isDetecting
                      ? Colors.blue.withOpacity(0.8)
                      : Colors.green.withOpacity(0.8),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  _isPaused
                      ? 'Paused'
                      : _isDetecting
                          ? 'Detecting...'
                          : 'Active',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// Custom painter for drawing bounding boxes and labels
class LiveDetectionPainter extends CustomPainter {
  final List<TrackedFruit> trackedFruits;
  final double imageWidth;
  final double imageHeight;

  LiveDetectionPainter({
    required this.trackedFruits,
    required this.imageWidth,
    required this.imageHeight,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (imageWidth == 0 || imageHeight == 0 || trackedFruits.isEmpty) return;

    // Calculate scale factors to map image coordinates to screen coordinates
    final scaleX = size.width / imageWidth;
    final scaleY = size.height / imageHeight;

    for (var fruit in trackedFruits) {
      final bbox = fruit.bbox;
      final x1 = (bbox[0] as num).toDouble() * scaleX;
      final y1 = (bbox[1] as num).toDouble() * scaleY;
      final x2 = (bbox[2] as num).toDouble() * scaleX;
      final y2 = (bbox[3] as num).toDouble() * scaleY;

      // Draw bounding box
      final paint = Paint()
        ..color = Colors.green
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.0;

      canvas.drawRect(
        Rect.fromLTRB(x1, y1, x2, y2),
        paint,
      );

      // Draw label background
      final labelText = '${fruit.className} #${fruit.id}';
      final textPainter = TextPainter(
        text: TextSpan(
          text: labelText,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();

      final labelY = y1 - textPainter.height - 8;
      final labelRect = Rect.fromLTWH(
        x1,
        labelY < 0 ? y1 : labelY,
        textPainter.width + 8,
        textPainter.height + 4,
      );

      // Draw label background
      final labelPaint = Paint()
        ..color = Colors.green.withOpacity(0.8)
        ..style = PaintingStyle.fill;
      canvas.drawRect(labelRect, labelPaint);

      // Draw label text
      textPainter.paint(
        canvas,
        Offset(x1 + 4, labelY < 0 ? y1 + 2 : labelY + 2),
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) {
    return true; // Always repaint for smooth updates
  }
}
