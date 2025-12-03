// ============================================================================
// HOME PAGE - Main detection interface
// ============================================================================
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';
import 'package:image/image.dart' as img;

// Widgets
import '../widgets/bounding_box_painter.dart';
import '../widgets/mode_toggle_button.dart';
import '../widgets/app_drawer.dart';
import '../widgets/ai_chat_widget.dart';

// Services
import '../services/model_service.dart';
import '../services/backend_service.dart';
import '../services/storage_service.dart';

// Models
import '../models/detection_record.dart';

enum AppState { initial, imageSelected, detecting, results }

class MyHomePage extends StatefulWidget {
  final Function(ThemeMode) onThemeToggle;

  const MyHomePage({
    super.key,
    required this.onThemeToggle,
  });

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  // ========================================================================
  // STATE VARIABLES
  // ========================================================================
  AppState _appState = AppState.initial;
  File? _image;
  List<Map<String, dynamic>>? _recognitions;
  double _imageHeight = 0.0;
  double _imageWidth = 0.0;

  // Image picker instance
  final picker = ImagePicker();

  // Model related
  Interpreter? _interpreter;
  List<String> _labels = [];
  final int _inputSize = 640;
  bool _modelLoaded = false;
  String? _modelLoadError;

  // Detection mode (offline/online)
  bool _useOnlineMode = false;
  bool _isOnline = false;
  final BackendDetectionService _backendService = BackendDetectionService();
  final Connectivity _connectivity = Connectivity();

  // AI Chat state
  bool _isChatOpen = false;

  // Fruit color mapping for UI display
  final Map<String, Color> _fruitColors = {
    'apple': Colors.red,
    'watermelon': Colors.green,
    'mango': const Color.fromARGB(255, 0, 64, 31),
    'strawberry': const Color.fromARGB(255, 231, 42, 209),
    'banana': Colors.yellow,
    'orange': Colors.orange,
    'pineapple': const Color.fromARGB(255, 152, 110, 3),
    'grape': Colors.purple,
    'grapes': Colors.purple, // Keep for backward compatibility
    'default': Colors.grey,
  };

  // ========================================================================
  // INITIALIZATION
  // ========================================================================
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadModelAndLabels();
      _loadDetectionMode();
      _checkConnectivity();
      _setupConnectivityListener();
    });
  }

  // Load saved detection mode preference
  Future<void> _loadDetectionMode() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _useOnlineMode = prefs.getBool('use_online_mode') ?? false;
    });
  }

  // Save detection mode preference
  Future<void> _saveDetectionMode(bool useOnline) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('use_online_mode', useOnline);
    setState(() {
      _useOnlineMode = useOnline;
    });
  }

  // Check internet connectivity
  Future<void> _checkConnectivity() async {
    try {
      final result = await _connectivity.checkConnectivity();
      setState(() {
        _isOnline = result != ConnectivityResult.none;
      });
    } catch (e) {
      setState(() {
        _isOnline = false;
      });
    }
  }

  // Listen for connectivity changes
  void _setupConnectivityListener() {
    _connectivity.onConnectivityChanged.listen((result) {
      setState(() {
        _isOnline = result != ConnectivityResult.none;
      });
    });
  }

  // ============================================================================
  // MODEL LOADING & MANAGEMENT
  // ============================================================================
  Future<void> _loadModelAndLabels() async {
    final result = await ModelService.loadModelAndLabels(context);
    if (!mounted) return;

    setState(() {
      _interpreter = result['interpreter'] as Interpreter?;
      _labels = result['labels'] as List<String>;
      _modelLoaded = result['modelLoaded'] as bool;
      _modelLoadError = result['error'] as String?;
    });
  }

  @override
  void dispose() {
    _interpreter?.close();
    super.dispose();
  }

  // ============================================================================
  // IMAGE DETECTION - MAIN PREDICTION FUNCTION
  // ============================================================================
  Future<void> _predictImage() async {
    if (_image == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("No image selected.")),
        );
      }
      return;
    }

    // Check if online mode is selected but device is offline
    if (_useOnlineMode && !_isOnline) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Not connected to internet"),
            duration: Duration(seconds: 3),
          ),
        );
      }
      return;
    }

    // Check if offline mode is selected but model not loaded
    if (!_useOnlineMode) {
      if (_interpreter == null || !_modelLoaded) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Model not ready. Please wait...")),
          );
        }
        return;
      }
    }

    setState(() => _appState = AppState.detecting);

    try {
      List<Map<String, dynamic>> recognitions;
      double imageWidth;
      double imageHeight;

      if (_useOnlineMode) {
        // Use backend server for detection
        print("🌐 Using online mode (backend server)");

        // Check server health first
        final isServerHealthy = await _backendService.checkHealth();
        if (!isServerHealthy) {
          throw Exception('Server not found');
        }

        // Get image dimensions
        final decodedImage = img.decodeImage(await _image!.readAsBytes());
        if (decodedImage == null) {
          throw Exception("Cannot decode image");
        }
        imageWidth = decodedImage.width.toDouble();
        imageHeight = decodedImage.height.toDouble();

        // Call backend service
        recognitions = await _backendService.detectFruits(_image!);
      } else {
        // Use offline TFLite model
        print("📱 Using offline mode (TFLite)");

        // Load model bytes in main thread (before isolate)
        final ByteData modelData =
            await DefaultAssetBundle.of(context).load('assets/model.tflite');
        final Uint8List modelBytes = modelData.buffer.asUint8List();

        // Prepare parameters for isolate
        final params = {
          'imagePath': _image!.path,
          'modelBytes': modelBytes,
          'labels': _labels,
          'inputSize': _inputSize,
        };

        // Run model in isolate
        final result = await compute(ModelService.runModelIsolate, params);

        recognitions = result['recognitions'] as List<Map<String, dynamic>>;
        imageWidth = result['imageWidth'] as double;
        imageHeight = result['imageHeight'] as double;

        // Scale bounding boxes to image coordinates
        recognitions = recognitions.map((rec) {
          final rect = rec['rect'] as Rect;
          return {
            'rect': Rect.fromLTRB(
              rect.left * imageWidth,
              rect.top * imageHeight,
              rect.right * imageWidth,
              rect.bottom * imageHeight,
            ),
            'detectedClass': rec['detectedClass'],
            'confidenceInClass': rec['confidenceInClass'],
          };
        }).toList();
      }

      if (!mounted) return;

      if (recognitions.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("No fruits detected.")),
        );
        setState(() => _appState = AppState.imageSelected);
      } else {
        setState(() {
          _recognitions = recognitions;
          _imageWidth = imageWidth;
          _imageHeight = imageHeight;
          _appState = AppState.results;
        });

        // Save detection to calendar
        _saveDetectionToCalendar(recognitions);
      }
    } catch (e, stackTrace) {
      print("❌ Error running detection: $e");
      print("❌ Stack trace: $stackTrace");
      if (!mounted) return;

      // Simple error messages
      String errorMessage;
      if (_useOnlineMode) {
        if (e.toString().contains("timeout") ||
            e.toString().contains("unreachable") ||
            e.toString().contains("Server not found") ||
            e.toString().contains("SocketException")) {
          errorMessage = "Not connected to internet or server not found";
        } else {
          errorMessage = "Server not found";
        }
      } else {
        errorMessage = "Detection failed";
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(errorMessage),
          duration: const Duration(seconds: 3),
        ),
      );
      setState(() => _appState = AppState.imageSelected);
    }
  }

  // ============================================================================
  // IMAGE PICKING - GALLERY & CAMERA
  // ============================================================================
  Future<void> _getImage(ImageSource source) async {
    try {
      setState(() {
        _appState = AppState.detecting; // Show loading while picking
      });

      final pickedFile = await picker.pickImage(source: source);

      if (pickedFile != null) {
        // Load image dimensions asynchronously
        final imageFile = File(pickedFile.path);
        final imageBytes = await imageFile.readAsBytes();
        final decodedImage = img.decodeImage(imageBytes);

        if (decodedImage != null) {
          setState(() {
            _image = imageFile;
            _imageWidth = decodedImage.width.toDouble();
            _imageHeight = decodedImage.height.toDouble();
            _appState = AppState.imageSelected;
            _recognitions = null;
          });
        } else {
          setState(() {
            _appState = AppState.initial;
          });
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text("Failed to load image")),
            );
          }
        }
      } else {
        setState(() {
          _appState = AppState.initial;
        });
      }
    } catch (e) {
      print("Error picking image: $e");
      setState(() {
        _appState = AppState.initial;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error: ${e.toString()}")),
        );
      }
    }
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================
  // Save detection results to calendar
  Future<void> _saveDetectionToCalendar(
      List<Map<String, dynamic>> recognitions) async {
    try {
      // Count fruits by type
      final Map<String, int> fruitCounts = {};
      for (var rec in recognitions) {
        final fruit = rec['detectedClass'] as String;
        fruitCounts[fruit] = (fruitCounts[fruit] ?? 0) + 1;
      }

      // Get current date
      final now = DateTime.now();
      final dateString = DateFormat('yyyy-MM-dd').format(now);

      // Create detection record
      final record = DetectionRecord(
        date: dateString,
        fruitCounts: fruitCounts,
        imagePath: _image?.path,
        timestamp: now,
      );

      // Save to storage
      await StorageService.saveDetection(record);
      print('✅ Detection saved to calendar: $fruitCounts');
    } catch (e) {
      print('⚠️ Error saving detection to calendar: $e');
      // Don't show error to user - it's not critical
    }
  }

  void _reset() {
    setState(() {
      _appState = AppState.initial;
      _image = null;
      _recognitions = null;
    });
  }

  // ============================================================================
  // THEME MANAGEMENT (DARK/LIGHT MODE TOGGLE)
  // ============================================================================
  // Get current theme mode from context
  ThemeMode _getCurrentThemeMode() {
    final brightness = Theme.of(context).brightness;
    if (brightness == Brightness.dark) {
      return ThemeMode.dark;
    } else {
      return ThemeMode.light;
    }
  }

  // Get next theme mode to toggle to
  ThemeMode _getNextThemeMode() {
    final current = _getCurrentThemeMode();
    switch (current) {
      case ThemeMode.light:
        return ThemeMode.dark;
      case ThemeMode.dark:
        return ThemeMode.light;
      case ThemeMode.system:
        return ThemeMode.light;
    }
  }

  // Get appropriate icon for current theme
  IconData _getThemeIcon() {
    final current = _getCurrentThemeMode();
    switch (current) {
      case ThemeMode.light:
        return Icons.light_mode;
      case ThemeMode.dark:
        return Icons.dark_mode;
      case ThemeMode.system:
        return Icons.brightness_auto;
    }
  }

  // ============================================================================
  // UI BUILDING - MAIN BUILD METHOD
  // ============================================================================
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final currentRoute = ModalRoute.of(context)?.settings.name ?? '/home';

    return Scaffold(
      drawer: AppDrawer(currentRoute: currentRoute),
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: const Text(""),
        centerTitle: true,
        leading: _isChatOpen
            ? null // Hide menu button when chat is open
            : Builder(
                builder: (context) => IconButton(
                  icon: const Icon(Icons.menu),
                  onPressed: () {
                    Scaffold.of(context).openDrawer();
                  },
                  tooltip: 'Menu',
                ),
              ),
        actions: _isChatOpen
            ? [] // Hide theme toggle when chat is open
            : [
                IconButton(
                  icon: Icon(_getThemeIcon()),
                  onPressed: () {
                    widget.onThemeToggle(_getNextThemeMode());
                    // Force rebuild to update icon
                    setState(() {});
                  },
                  tooltip: 'Toggle theme',
                ),
              ],
      ),
      body: Stack(
        children: [
          SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 82, 24, 100),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text(
                  "AI-Powered Image Recognition",
                  style: TextStyle(
                    fontSize: 16,
                    color: isDark ? Colors.grey[400] : Colors.grey[600],
                  ),
                ),
                const SizedBox(height: 20),
                if (!_modelLoaded)
                  Column(
                    children: [
                      const Text(
                        "Loading model, please wait...",
                        style: TextStyle(color: Colors.redAccent, fontSize: 14),
                      ),
                      if (_modelLoadError != null) ...[
                        const SizedBox(height: 8),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16.0),
                          child: Text(
                            _modelLoadError!,
                            style: const TextStyle(
                              color: Colors.orange,
                              fontSize: 12,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],
                    ],
                  )
                else if (_appState != AppState.detecting)
                  // Mode toggle button in the center (only show when model is loaded and not detecting)
                  Center(
                    child: ModeToggleButton(
                      isOnlineMode: _useOnlineMode,
                      canUseOnline: _isOnline,
                      onTap: () {
                        _saveDetectionMode(!_useOnlineMode);
                      },
                    ),
                  ),
                const SizedBox(height: 20),
                _buildCurrentStateWidget(),
              ],
            ),
          ),
          // AI Chat Widget (combined button and popup)
          AIChatWidget(
            onChatStateChanged: (isOpen) {
              setState(() {
                _isChatOpen = isOpen;
              });
            },
          ),
        ],
      ),
    );
  }

  // ============================================================================
  // UI BUILDING METHODS - SCREEN STATES
  // ============================================================================
  Widget _buildCurrentStateWidget() {
    switch (_appState) {
      case AppState.initial:
        return _buildInitialScreen();
      case AppState.imageSelected:
        return _buildImageSelectedScreen();
      case AppState.detecting:
        return const Center(child: CircularProgressIndicator());
      case AppState.results:
        return _buildResultsScreen();
    }
  }

  // Initial screen - No image selected
  Widget _buildInitialScreen() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      children: [
        Container(
          height: 250,
          width: double.infinity,
          decoration: BoxDecoration(
            border: Border.all(
              color: isDark ? Colors.grey[700]! : Colors.grey.shade300,
              width: 2,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.image_search,
                size: 80,
                color: isDark ? Colors.grey[600] : Colors.grey,
              ),
              const SizedBox(height: 16),
              const Text("No Image Selected",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40.0),
                child: Text(
                  "Capture or select an image to detect fruits",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: isDark ? Colors.grey[400] : Colors.grey,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 32),
        // Modern side-by-side action cards
        Row(
          children: [
            Expanded(
              child: _buildModernActionCard(
                title: "Capture",
                subtitle: "Take Photo",
                icon: Icons.camera_alt_rounded,
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF4CAF50),
                    Color(0xFF45A049),
                  ],
                ),
                onTap: () => _getImage(ImageSource.camera),
                isDark: isDark,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _buildModernActionCard(
                title: "Gallery",
                subtitle: "Choose Image",
                icon: Icons.photo_library_rounded,
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: isDark
                      ? [
                          const Color(0xFF6C757D),
                          const Color(0xFF5A6268),
                        ]
                      : [
                          const Color(0xFF9E9E9E),
                          const Color(0xFF757575),
                        ],
                ),
                onTap: () => _getImage(ImageSource.gallery),
                isDark: isDark,
              ),
            ),
          ],
        ),
      ],
    );
  }

  // Modern action card with gradient and modern styling
  Widget _buildModernActionCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required Gradient gradient,
    required VoidCallback onTap,
    required bool isDark,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: gradient,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: gradient.colors[0].withOpacity(0.3),
                blurRadius: 15,
                offset: const Offset(0, 8),
                spreadRadius: 0,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(
                  icon,
                  size: 32,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.white.withOpacity(0.9),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Image selected screen - Shows selected image with detect button
  Widget _buildImageSelectedScreen() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      children: [
        Container(
          decoration: BoxDecoration(
            border: Border.all(
              color: isDark ? Colors.grey[700]! : Colors.grey.shade300,
              width: 1,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(_image!),
              ),
              Positioned(
                top: 8,
                left: 8,
                child: CircleAvatar(
                  backgroundColor: Colors.black54,
                  child: IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: _reset,
                  ),
                ),
              )
            ],
          ),
        ),
        const SizedBox(height: 24),
        _buildGreenButton("Detect Fruits", _predictImage),
      ],
    );
  }

  // Results screen - Shows detections with bounding boxes
  Widget _buildResultsScreen() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    Map<String, int> fruitCounts = {};
    for (var rec in _recognitions ?? []) {
      String detectedClass = rec['detectedClass'];
      fruitCounts[detectedClass] = (fruitCounts[detectedClass] ?? 0) + 1;
    }

    return Column(
      children: [
        // Show the image with bounding boxes
        Container(
          decoration: BoxDecoration(
            border: Border.all(
              color: isDark ? Colors.grey[700]! : Colors.grey.shade300,
              width: 1,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Stack(
              children: [
                Image.file(_image!),
                if (_recognitions != null &&
                    _recognitions!.isNotEmpty &&
                    _imageWidth > 0 &&
                    _imageHeight > 0)
                  LayoutBuilder(
                    builder: (context, constraints) {
                      return CustomPaint(
                        painter: BoundingBoxPainter(
                          recognitions: _recognitions!,
                          fruitColors: _fruitColors,
                          imageWidth: _imageWidth,
                          imageHeight: _imageHeight,
                        ),
                        size: Size.infinite,
                        child: SizedBox(
                          width: constraints.maxWidth,
                          height: constraints.maxWidth *
                              (_imageHeight / _imageWidth),
                        ),
                      );
                    },
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        Text(
          "Total Fruits Detected",
          style: TextStyle(
            fontSize: 18,
            color: isDark ? Colors.grey[400] : Colors.grey,
          ),
        ),
        Text((_recognitions?.length ?? 0).toString(),
            style: const TextStyle(fontSize: 56, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        ...fruitCounts.entries
            .map((entry) => _buildResultRow(entry.key, entry.value)),
        const SizedBox(height: 30),
        _buildGreyButton("Detect Another Image", _reset, isOutlined: true),
      ],
    );
  }

  // ============================================================================
  // UI BUILDING METHODS - RESULT DISPLAY COMPONENTS
  // ============================================================================
  // Build a row showing fruit count
  Widget _buildResultRow(String fruit, int count) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          children: [
            Container(
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                color: _fruitColors[fruit.toLowerCase()] ??
                    _fruitColors['default'],
                borderRadius: BorderRadius.circular(5),
              ),
            ),
            const SizedBox(width: 16),
            Text(fruit,
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w500)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: isDark ? Colors.grey[800] : Colors.grey.shade200,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                count.toString(),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : Colors.black87,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============================================================================
  // UI BUILDING METHODS - BUTTON COMPONENTS
  // ============================================================================
  // Green primary button (for main actions)
  Widget _buildGreenButton(String text, VoidCallback onPressed,
      {IconData? icon}) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.green,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 16),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        child: (icon != null)
            ? Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(icon),
                const SizedBox(width: 10),
                Text(text, style: const TextStyle(fontSize: 16))
              ])
            : Text(text, style: const TextStyle(fontSize: 16)),
      ),
    );
  }

  // Grey secondary button (for secondary actions)
  Widget _buildGreyButton(String text, VoidCallback onPressed,
      {IconData? icon, bool isOutlined = false}) {
    return SizedBox(
      width: double.infinity,
      child: isOutlined
          ? OutlinedButton(
              onPressed: onPressed,
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.grey.shade700,
                side: BorderSide(color: Colors.grey.shade400),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10)),
              ),
              child: Text(text, style: const TextStyle(fontSize: 16)),
            )
          : ElevatedButton(
              onPressed: onPressed,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.grey.shade300,
                foregroundColor: Colors.grey.shade800,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10)),
                elevation: 0,
              ),
              child: (icon != null)
                  ? Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(icon),
                        const SizedBox(width: 10),
                        Text(text, style: const TextStyle(fontSize: 16)),
                      ],
                    )
                  : Text(text, style: const TextStyle(fontSize: 16)),
            ),
    );
  }
}
