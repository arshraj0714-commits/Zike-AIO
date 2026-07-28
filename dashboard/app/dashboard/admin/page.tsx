/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║                                                                  ║
 * ║   ░█▀▀░█▀█░█▀▄░█▀▀░█░█   ░█▀▄░█▀▀░█░█░█▀▀                     ║
 * ║   ░█░░░█░█░█░█░█▀▀░▄▀▄   ░█░█░█▀▀░▀▄▀░▀▀█                     ║
 * ║   ░▀▀▀░▀▀▀░▀▀░░▀▀▀░▀░▀   ░▀▀░░▀▀▀░░▀░░▀▀▀                     ║
 * ║                                                                  ║
 * ║            © 2026 Arsh — All Rights Reserved                    ║
 * ║                                                                  ║
 * ║            Built by  ──  Arsh                                    ║
 * ║                                                                  ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */

import React from "react";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";
import { isAdmin, cn } from "@/lib/utils";
import { Shield, Users, Server, Activity, Database, Cpu, Globe, Lock, Settings } from "lucide-react";

import { AdminContent } from "@/components/dashboard/admin-content";

export default async function AdminPage() {
  const session = await getServerSession(authOptions);
  
  // Server-side protection
  if (!session || !isAdmin(session.user?.id)) {
    redirect("/dashboard");
  }

  return <AdminContent />;
}


