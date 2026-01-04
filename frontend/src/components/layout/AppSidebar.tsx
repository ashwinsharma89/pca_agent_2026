"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
    Upload,
    BarChart3,
    MessageSquare,
    Settings,
    List,
    Activity,
    TrendingUp,
    FileSpreadsheet,
    Globe
} from "lucide-react";

type SidebarProps = React.HTMLAttributes<HTMLDivElement>;

export function AppSidebar({ className }: SidebarProps) {
    const pathname = usePathname();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        const raf = requestAnimationFrame(() => {
            setMounted(true);
        });
        return () => cancelAnimationFrame(raf);
    }, []);

    if (pathname === "/login") return null;

    const items = [
        // {
        //     title: "Dashboard",
        //     href: "/dashboard",
        //     icon: LayoutDashboard,
        // },
        {
            title: "Upload Data",
            href: "/upload",
            icon: Upload,
        },
        {
            title: "Visualizations",
            href: "/visualizations",
            icon: BarChart3,
        },
        {
            title: "Ads Overview",
            href: "/visualizations-2",
            icon: BarChart3,
        },
        {
            title: "Analysis",
            href: "/analysis",
            icon: BarChart3, // Changed icon to BarChart3
        },
        {
            title: "Analytics Studio",
            href: "/in-depth-analysis", // Added new item
            icon: Activity,
        },
        {
            title: "Regression",
            href: "/regression",
            icon: TrendingUp,
        },
        {
            title: "Q&A",
            href: "/chat",
            icon: MessageSquare,
        },
        {
            title: "Campaigns List",
            href: "/campaigns",
            icon: List,
        },
        {
            title: "Pacing Reports",
            href: "/pacing-reports",
            icon: FileSpreadsheet,
        },
        {
            title: "API Connections",
            href: "/ad-explorer",
            icon: Globe,
        },
        {
            title: "Settings",
            href: "/settings",
            icon: Settings,
        },
    ];

    return (
        <div className={cn("pb-12 w-64 border-r border-border min-h-screen bg-card", className)}>
            <div className="space-y-4 py-4">
                <div className="px-3 py-2">
                    <h2 className="mb-2 px-4 text-xl font-semibold tracking-tight text-foreground">
                        PCA Agent
                    </h2>
                    <div className="space-y-1">
                        {items.map((item) => (
                            <Button
                                key={item.href}
                                variant={pathname === item.href ? "secondary" : "ghost"}
                                className="w-full justify-start"
                                asChild
                            >
                                <Link href={item.href}>
                                    <item.icon className="mr-2 h-4 w-4" />
                                    {item.title}
                                </Link>
                            </Button>
                        ))}
                    </div>
                </div>

                {/* Theme Toggle - Only render on client side */}
                {mounted && (
                    <div className="px-3 py-2 border-t border-border">
                        <div className="px-4 py-2 flex items-center justify-between">
                            <span className="text-sm font-medium text-foreground">Theme</span>
                            <ThemeToggle />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
