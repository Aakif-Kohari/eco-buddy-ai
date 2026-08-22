import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    LayoutDashboard, 
    Leaf, 
    Activity, 
    Factory, 
    Settings, 
    Menu, 
    X, 
    Bell,
    UserCircle,
    LogOut,
    Sun,
    Moon
} from 'lucide-react';
import EsgDashboardContainer from './components/EsgDashboardContainer';
import { EsgMetricsProvider } from './services/EsgMetricsService';

import './index.css'; // Assuming Tailwind is configured

interface NavigationItem {
    id: string;
    label: string;
    icon: React.FC<{ className?: string }>;
}

const NAV_ITEMS: NavigationItem[] = [
    { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
    { id: 'emissions', label: 'Carbon Footprint', icon: Factory },
    { id: 'sustainability', label: 'Sustainability Goals', icon: Leaf },
    { id: 'analytics', label: 'Advanced Analytics', icon: Activity },
    { id: 'settings', label: 'Preferences', icon: Settings },
];

export const App: React.FC = () => {
    const [isSidebarOpen, setSidebarOpen] = useState(true);
    const [activeView, setActiveView] = useState<string>('dashboard');
    const [theme, setTheme] = useState<'dark' | 'light'>('dark');

    // Toggle Sidebar
    const toggleSidebar = () => setSidebarOpen(prev => !prev);

    // Toggle Theme
    const toggleTheme = () => {
        const newTheme = theme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
        document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', newTheme);
    };

    // Initialize Theme
    useEffect(() => {
        const saved = localStorage.getItem('theme');
        if (saved && (saved === 'dark' || saved === 'light')) {
            setTheme(saved as 'dark' | 'light');
            if (saved === 'dark') document.documentElement.classList.add('dark');
            else document.documentElement.classList.remove('dark');
        } else {
            document.documentElement.classList.add('dark');
        }
    }, []);

    const sidebarVariants = {
        open: { width: '256px', transition: { type: 'spring', stiffness: 300, damping: 30 } },
        closed: { width: '80px', transition: { type: 'spring', stiffness: 300, damping: 30 } }
    };

    const textVariants = {
        open: { opacity: 1, display: 'block', transition: { delay: 0.1 } },
        closed: { opacity: 0, display: 'none', transition: { duration: 0.1 } }
    };

    return (
        <EsgMetricsProvider>
            <div className={`flex h-screen w-full bg-slate-50 dark:bg-slate-900 transition-colors duration-300 font-sans overflow-hidden ${theme}`}>
                
                {/* SIDEBAR NAVIGATION */}
                <motion.aside
                    initial="open"
                    animate={isSidebarOpen ? 'open' : 'closed'}
                    variants={sidebarVariants}
                    className="relative z-20 flex flex-col bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 shadow-xl"
                >
                    <div className="flex items-center justify-between h-20 px-4 py-6 border-b border-slate-200 dark:border-slate-700">
                        <motion.div 
                            className="flex items-center gap-3"
                            animate={isSidebarOpen ? 'open' : 'closed'}
                        >
                            <div className="p-2 bg-emerald-500 rounded-lg shadow-lg shadow-emerald-500/30">
                                <Leaf className="w-6 h-6 text-white" />
                            </div>
                            <motion.span 
                                variants={textVariants}
                                className="text-xl font-bold font-display text-slate-800 dark:text-white tracking-tight"
                            >
                                Eco Buddy Al
                            </motion.span>
                        </motion.div>
                    </div>

                    <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto">
                        {NAV_ITEMS.map((item) => {
                            const Icon = item.icon;
                            const isActive = activeView === item.id;
                            return (
                                <button
                                    key={item.id}
                                    onClick={() => setActiveView(item.id)}
                                    className={`
                                        w-full flex items-center gap-4 px-3 py-3 rounded-xl transition-all duration-200 group relative
                                        ${isActive 
                                            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' 
                                            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50 hover:text-slate-900 dark:hover:text-slate-200'}
                                    `}
                                >
                                    {isActive && (
                                        <motion.div 
                                            layoutId="active-indicator"
                                            className="absolute left-0 w-1 h-8 bg-emerald-500 rounded-r-full"
                                            initial={false}
                                        />
                                    )}
                                    <Icon className={`w-5 h-5 flex-shrink-0 transition-transform duration-200 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
                                    <motion.span 
                                        variants={textVariants}
                                        className="font-medium whitespace-nowrap"
                                    >
                                        {item.label}
                                    </motion.span>
                                </button>
                            );
                        })}
                    </nav>

                    <div className="p-4 border-t border-slate-200 dark:border-slate-700">
                        <button className="w-full flex items-center gap-4 px-3 py-3 rounded-xl text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors">
                            <LogOut className="w-5 h-5 flex-shrink-0" />
                            <motion.span variants={textVariants} className="font-medium">Sign Out</motion.span>
                        </button>
                    </div>
                </motion.aside>

                {/* MAIN CONTENT AREA */}
                <main className="flex-1 flex flex-col h-full bg-slate-50 dark:bg-slate-900 overflow-hidden relative">
                    
                    {/* TOP APP BAR */}
                    <header className="h-20 flex items-center justify-between px-8 bg-white/70 dark:bg-slate-800/70 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 z-10 sticky top-0 transition-colors">
                        <div className="flex items-center gap-4">
                            <button 
                                onClick={toggleSidebar}
                                className="p-2 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                            >
                                {isSidebarOpen ? <Menu className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                            </button>
                            <h1 className="text-2xl font-bold text-slate-800 dark:text-white tracking-tight capitalize">
                                {activeView.replace('-', ' ')}
                            </h1>
                        </div>

                        <div className="flex items-center gap-4">
                            <button 
                                onClick={toggleTheme}
                                className="p-2 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-all hover:scale-105"
                            >
                                {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                            </button>
                            
                            <div className="relative">
                                <button className="p-2 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-all hover:scale-105">
                                    <Bell className="w-5 h-5" />
                                </button>
                                <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 border-2 border-white dark:border-slate-800 rounded-full animate-pulse"></span>
                            </div>

                            <div className="h-8 w-px bg-slate-300 dark:bg-slate-700 mx-2"></div>

                            <button className="flex items-center gap-3 p-1 pr-3 rounded-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors border border-transparent dark:border-slate-600">
                                <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center shadow-inner">
                                    <UserCircle className="w-5 h-5 text-white" />
                                </div>
                                <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Admin User</span>
                            </button>
                        </div>
                    </header>

                    {/* DYNAMIC VIEW ROUTING */}
                    <div className="flex-1 overflow-x-hidden overflow-y-auto relative w-full h-full custom-scrollbar">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeView}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ duration: 0.25, ease: "easeInOut" }}
                                className="w-full h-full"
                            >
                                {activeView === 'dashboard' ? (
                                    <EsgDashboardContainer />
                                ) : (
                                    <div className="flex items-center justify-center w-full h-full">
                                        <div className="text-center space-y-4">
                                            <div className="w-24 h-24 mx-auto bg-slate-200 dark:bg-slate-800 rounded-full flex items-center justify-center animate-pulse">
                                                <Activity className="w-10 h-10 text-slate-400 dark:text-slate-600" />
                                            </div>
                                            <h2 className="text-2xl font-semibold text-slate-700 dark:text-slate-300">
                                                {activeView} module under construction
                                            </h2>
                                            <p className="text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                                                This section is part of the high-velocity enterprise pipeline and will be available in the next deployment cycle.
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </motion.div>
                        </AnimatePresence>
                    </div>
                </main>
            </div>
        </EsgMetricsProvider>
    );
};

export default App;
