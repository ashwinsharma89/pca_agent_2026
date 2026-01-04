'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import {
    Settings,
    LogOut,
    Bot,
    Upload,
    BarChart3,
    Activity,
    BarChart,
    MessageSquare,
    Layout,
    FileText,
    Sparkles,
    Scale,
    TrendingUp,
    Zap,
    AlertTriangle,
    Brain,
    Palette,
    Globe
} from 'lucide-react';

export function DashboardLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { user, logout, isLoading } = useAuth();
    const router = useRouter();

    React.useEffect(() => {
        if (!isLoading && !user) {
            router.push('/login');
        }
    }, [isLoading, user, router]);

    if (isLoading || !user) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    <Bot className="h-10 w-10 animate-bounce text-primary" />
                    <p className="text-muted-foreground">Loading application...</p>
                </div>
            </div>
        )
    }

    const navItems = [
        // { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { href: '/upload', label: 'Upload Data', icon: Upload },
        { href: '/analysis', label: 'Analysis', icon: BarChart3 },
        { href: '/visualizations', label: 'Visualizations', icon: BarChart },
        { href: '/visualizations-2', label: 'Executive Overview', icon: Palette },
        { href: '/in-depth-analysis', label: 'Analytics Studio', icon: Activity },
        { href: '/dashboard-builder', label: 'Dashboard Builder', icon: Layout },
        { href: '/intelligence-studio', label: 'Intelligence Studio', icon: Brain },
        { href: '/ai-insights', label: 'AI Insights', icon: Sparkles },
        { href: '/regression', label: 'Regression', icon: TrendingUp },
        { href: '/chat', label: 'Q&A', icon: MessageSquare },
        { href: '/ad-explorer', label: 'API Connections', icon: Globe },
        { href: '/settings', label: 'Settings', icon: Settings },
    ];

    return (
        <div className="flex min-h-screen bg-background">
            {/* Sidebar */}
            <aside className="fixed inset-y-0 left-0 z-20 w-64 border-r border-white/10 bg-black/40 backdrop-blur-xl">
                <div className="flex h-16 items-center border-b border-white/10 px-6">
                    <Link href="/campaigns" className="flex items-center gap-2 font-bold text-lg">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary">
                            <Bot className="h-5 w-5" />
                        </div>
                        PCA Agent
                    </Link>
                </div>

                <div className="flex flex-col justify-between h-[calc(100vh-64px)] p-4">
                    <nav className="space-y-2 flex-1 overflow-y-auto no-scrollbar">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${isActive
                                        ? 'bg-primary/10 text-primary'
                                        : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                                        }`}
                                >
                                    <Icon className="h-4 w-4" />
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="border-t border-white/10 pt-4">
                        <div className="mb-4 px-4">
                            <p className="text-sm font-medium">{user.username}</p>
                            <p className="text-xs text-muted-foreground truncate" title={user.email}>{user.email}</p>
                        </div>
                        <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-red-400" onClick={logout}>
                            <LogOut className="mr-2 h-4 w-4" />
                            Logout
                        </Button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 pl-64 pr-4 overflow-x-hidden">
                <div className="mx-auto px-4 py-8">
                    {children}
                </div>
            </main>
        </div>
    );
}
