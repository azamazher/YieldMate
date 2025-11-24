// ============================================================================
// APP CONFIGURATION & THEME MANAGEMENT
// ============================================================================
import 'package:flutter/material.dart';
import '../pages/home_page.dart';
import '../widgets/splash_screen.dart';
import '../pages/calendar_page.dart';
import '../pages/fruit_doctor_page.dart';
import '../pages/community_page.dart';
import '../pages/about_page.dart';

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  // Theme state management
  ThemeMode _themeMode = ThemeMode.system;

  // Toggle theme between light and dark mode
  void _toggleTheme(ThemeMode mode) {
    setState(() {
      _themeMode = mode;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      // Light theme configuration
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.green,
          brightness: Brightness.light,
        ),
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 0,
        ),
      ),
      // Dark theme configuration
      darkTheme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.green,
          brightness: Brightness.dark,
        ),
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 0,
        ),
      ),
      themeMode: _themeMode,
      // Routes
      routes: {
        '/': (context) => SplashScreen(
              onFinish: _toggleTheme,
              initialThemeMode: _themeMode,
            ),
        '/home': (context) => MyHomePage(
              onThemeToggle: _toggleTheme,
            ),
        '/calendar': (context) => const CalendarPage(),
        '/fruit-doctor': (context) => const FruitDoctorPage(),
        '/community': (context) => const CommunityPage(),
        '/about': (context) => const AboutPage(),
      },
      initialRoute: '/',
    );
  }
}
