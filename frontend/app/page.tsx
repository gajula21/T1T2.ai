"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LandingPage() {
  const router = useRouter();
  const { user } = useAuth();

  return (
    <div className="flex flex-col items-center pt-24 px-4 max-w-4xl mx-auto text-center">
      {/* Hero */}
      <h1 className="text-3xl font-bold mb-4">
        IELTS writing evaluator
      </h1>
      <p className="text-[#A3A3A3] text-sm max-w-lg mb-14">
        Get instant band scores and detailed feedback on your essays,
        powered by AI and calibrated to official IELTS rubrics.
      </p>

      {/* Task Cards Container */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl text-left">
        
        {/* Task 1 Card */}
        <Link href="/evaluate/task1" className="card-container p-6 flex flex-col items-start transition-colors hover:bg-[#383838]">
          <div className="bg-[#2563EB] text-white text-[10px] font-bold px-2 py-0.5 rounded-full mb-4">
            Task 1
          </div>
          <h2 className="text-base font-bold mb-2">Academic writing</h2>
          <p className="text-sm text-[#A3A3A3] leading-relaxed">
            Upload a chart or graph and submit your 150-word description for full band feedback.
          </p>
        </Link>

        {/* Task 2 Card */}
        <Link href="/evaluate/task2" className="card-container p-6 flex flex-col items-start transition-colors hover:bg-[#383838]">
          <div className="bg-[#16A34A] text-white text-[10px] font-bold px-2 py-0.5 rounded-full mb-4">
            Task 2
          </div>
          <h2 className="text-base font-bold mb-2">Essay writing</h2>
          <p className="text-sm text-[#A3A3A3] leading-relaxed">
            Submit your 250-word argumentative essay and receive criterion-by-criterion scoring.
          </p>
        </Link>
      </div>
    </div>
  );
}
