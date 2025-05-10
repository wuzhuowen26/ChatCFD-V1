import os
import json
import requests
from openai import OpenAI
from duckduckgo_search import DDGS
from tavily import TavilyClient

API_KEY = "d28ed432-bb2d-4efe-971d-7041a7f924f6"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

FUNCTIONS = [
    {
        "name": "search_duckduckgo",
        "description": "使用DuckDuckGo搜索引擎查询信息。可以搜索最新新闻、文章、博客等内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "搜索的关键词列表。例如：['Python', '机器学习', '最新进展']。"
                }
            },
            "required": ["keywords"]
        }
    }
]

def search_duckduckgo(keywords):
    search_term = " ".join(keywords)
    with DDGS() as ddgs:
        results = list(ddgs.text(keywords=search_term, region="cn-zh", safesearch="on", max_results=5))
    return results  # 将返回值放到函数末尾

def print_search_results(results):
    for result in results:
        print(
            f"标题: {result['title']}\n链接: {result['href']}\n摘要: {result['body']}\n---")

def get_openai_response(messages, model="deepseek-v3-250324", functions=None, function_call=None):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            functions=functions,
            function_call=function_call
        )
        return response.choices[0].message
    except Exception as e:
        print(f"调用OpenAI API时出错: {str(e)}")
        return None

def process_function_call(response_message):
    function_name = response_message.function_call.name
    function_args = json.loads(response_message.function_call.arguments)

    print(f"\n模型选择调用函数: {function_name}")

    if function_name == "search_duckduckgo":
        keywords = function_args.get('keywords', [])

        if not keywords:
            print("错误：模型没有提供搜索关键词")
            return None

        print(f"关键词: {', '.join(keywords)}")

        function_response = search_duckduckgo(keywords)
        print("\nDuckDuckGo搜索返回结果:")
        print_search_results(function_response)

        return function_response
    else:
        print(f"未知的函数名称: {function_name}")
        return None

def main(question):
    print(f"问题：{question}")

    messages = [{"role": "user", "content": question}]
    response_message = get_openai_response(
        messages, functions=FUNCTIONS, function_call={"name": "search_duckduckgo"}
    )

    if not response_message:
        print("模型没有返回任何内容")
        return 

    print("\n模型回答:")
    print(response_message.content)

    print("\n模型返回的函数调用:", response_message.function_call)
    if response_message.function_call:
        print(f"\n模型返回函数调用: {response_message.function_call.name}")
        if not response_message.content:
            response_message.content = ""
        function_response = process_function_call(response_message)

        if function_response:
            messages.extend([
                response_message.model_dump(),
                {
                    "role": "function",
                    "name": response_message.function_call.name,
                    "content": json.dumps(function_response, ensure_ascii=False)
                }
            ])

        final_response = get_openai_response(messages, model="deepseek-v3-250324")

        if final_response:
            print("\n最终回答:")
            print(final_response.content)
        else:
            print("\n模型直接回答:")
            print(response_message.content)

def test_connection(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"成功连接到 {url}")
        else:
            print(f"无法连接到 {url}, 状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {str(e)}")


if __name__ == "__main__":
    # main("用DuckDuckGo搜索引擎查询信息,现在几点了")
    result = search_duckduckgo(["Python", "机器学习", "最新进展"])
    print(result)
    # print_search_results(result)


    # test_connection("https://duckduckgo.com/")

    # 执行简单的搜索
    # results = DDGS().text("python programming", max_results=5)
    # print(results)

    
#     client = TavilyClient("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")
#     response = client.search(
#         query="what is the time in beijing now"
#     )
#     response = client.extract(
#         urls=["https://www.thetimenow.com/china/beijing"]
#     )
#     print(response)

#     question = "According to the next information, what is the time in beijing now?"+ str(response)

#     messages = [{"role": "user", "content": question}]
#     client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

#     response_message = get_openai_response(messages)

#     if not response_message:
#         print("模型没有返回任何内容")

#     print("\n模型回答:")
#     print(response_message.content)

# {
#   "results": [
#     {
#       "url": "https://www.cfd-online.com/Forums/openfoam/258292-buoyantpimplefoam-natural-convection-free-openings-setup.html",
#       "raw_content": " |  |  |  |  | [Sponsors]\n | \n\n | \n\nHomeNewsIndexPost NewsSubscribe/UnsubscribeForumsMain CFD ForumSystem AnalysisStructural MechanicsElectromagneticsCFD FreelancersHardware ForumLoungeSoftware User ForumsANSYSCFXFLUENTMeshing & GeometryAutodeskAVL FIRECOMSOLCONVERGEFidelity CFDFloEFD & FloTHERMFLOW-3DOpenFOAMNews & AnnouncementsInstallationMeshingPre-ProcessingSolvingPost-ProcessingProgrammingVerification & ValidationCommunity ContributionsJournalBugsPhoenicsREEF3DNews & AnnouncementsSiemensSTAR-CCM+STAR-CDSU2News & AnnouncementsInstallationShape DesignPre-processorsANSAenGridGridProPointwisePost-ProcessorsEnSightFieldViewParaViewTecplotSpecial TopicsMesh GenerationVisualizationCFD Online CommunitySite NewsSite Help & DiscussionsCFD-WikiWikiIntroductionRecent ChangesReference SectionFluid DynamicsTurbulence ModelingNumerical MethodsMeshingSpecial TopicsAero-AcousticsCombustionParallel ComputingTurbulenceApplication AreasAerospaceAutomotiveTurbomachineryBest Practice GuidesAutomotive CFDTurbomachiney CFDHeat Transfer CFDValidation CasesCodesSource Code ArchiveFAQ'sAnsysCHAMCONVERGEFluentMetaconpMeteoDynSiemensHistory of CFDAbout CFD-WikiHelpFAQGetting StartedCommunity PortalDonate TextsDonated TextsLinksWhat's NewIntroductionModeling & NumericsTurbulenceCombustionDiscretization SchemesSolversMultigrid MethodsFinite Element MethodsCartesian Methods / AMRNumerial AnalysisMesh GenerationGeneral ResourcesSelected ProjectsCompaniesProgramming & Dev.Data FormatsSoftware LibrariesNumerical SoftwareParallel ComputingGeneral SitesSoftwareFluid DynamicsMesh GenerationVisualizationCommercial CFD CodesHardwareBenchmarksNews and ReviewsHardware VendorsCloudsClustersGPGPUMiscReferencesValidation CasesAirfoilsMaterial PropertiesGlossariesFinding DocumentsPreprints OnlinePapers & ReportsBooksJournalsPublishersOnline ToolsUnit ConvertersCalculatorsy+ EstimationCompressible FlowHeat TransferAirfoil GeneratorsSimple CasesCombustionCycles & ProcessesOnline Books & GuidesCFD IntroductionsBooksBest Practice GuidelinesFluid & Aero DynamicsSeminarsEncyclopediasSocial MediaDiscussion ForumsBlogsTwitterYouTubeFacebookLinkedInPodcastsUsenet NewsgroupsMailing ListsChatsNewsEducationCFD ProgrammesOnline LabsOnline CoursesCourse MaterialJobsCFD Job ResourcesCompanies & Orgs.General ResourcesEventsEvent CalendarsSpecific OrganizationsVendor Events ListsMiscPictures and MoviesFunLinks to LinksSuggest New LinkAbout this SectionJobsPost Job AdList All JobsList Jobs by TypeJob in Industry (24)Job in Academia (27)Contract Work (3)PostDoc Position (25)PhD Studentship (53)Internship (3)List Jobs by LocationAfricaMorroco (1)AsiaChina (9)Hong Kong (1)India (18)Iraq (1)Saudi Arabia (3)South Korea (1)Taiwan (1)Thailand (3)Turkey (2)United Arab Emirates (1)EuropeAustria (1)Belgium (3)Czech Republic (1)France (16)Germany (4)Italy (1)Luxembourg (1)Netherlands (5)Norway (1)Poland (2)Spain (2)Sweden (1)Switzerland (1)United Kingdom (25)North AmericaCanada (4)United States (22)OceaniaAustralia (2)New Zealand (1)South AmericaBrazil (1)Search Job AdsEventsPost New EventList All EventsList Events by TypeConferences (12)Workshops (1)Courses (15)Seminars (2)Online Events (2)List Events by LocationAfricaAlgeria (1)AsiaIndia (13)Japan (1)EuropeAustria (4)Belgium (3)Denmark (1)Germany (4)Italy (2)Netherlands (1)Sweden (1)ToolsRPN CalculatorScientific CalculatorUnit ConversionY+ EstimationTurbulence PropertiesFeedsNewsBlogsVendorsJobsJournalsAboutAbout CFD OnlinePrivacy PolicyContacts & FeedbackWeb Server StatisticsList of SponsorsAdvertising on this SiteSearch\nBlogs\nRecent Entries\nBest Entries\nBest Blogs\nBlog List\nSearch Blogs\nbuoyantPimpleFoam: natural convection with free openings setup | User NameRemember MePassword | User Name |  | Remember Me | Password |  | \nUser Name |  | Remember Me\nPassword |  | \nbuoyantPimpleFoam: natural convection with free openings setup\n\nUser Name |  | Remember Me\nPassword |  | \nRegister | Blogs | Community | New Posts | Updated Threads | Search\nNew Today\nAll Forums\nMain CFD Forum\nANSYS - CFX\nANSYS - FLUENT\nANSYS - Meshing\nSiemens\nOpenFOAM\nSU2\nLast Week\nAll Forums\nMain CFD Forum\nANSYS - CFX\nANSYS - FLUENT\nANSYS - Meshing\nSiemens\nOpenFOAM\nSU2\nUpdated Today\nAll Forums\nMain CFD Forum\nANSYS - CFX\nANSYS - FLUENT\nANSYS - Meshing\nSiemens\nOpenFOAM\nSU2\nLast Week\nAll Forums\nMain CFD Forum\nANSYS - CFX\nANSYS - FLUENT\nANSYS - Meshing\nSiemens\nOpenFOAM\nSU2\nCommunity Links\nMembers List\nSearch Forums\nShow ThreadsShow Posts\nTag Search\nAdvanced Search\nSearch Blogs\n\nTag Search\nAdvanced Search\nGo to Page...\n\n\n | LinkBack | Thread Tools | Search this Thread | Display Modes\nOctober 30, 2024, 08:38 | buoyantPimpleFoam: natural convection with free openings setup | #1\nSadBoySquadNew MemberJoin Date: May 2021Location: Athens, GreecePosts: 28Rep Power:5 | Greetings to all FOAM'ers here!I am still trying to find a proper setup for a natural convection + buoyancy case with multiple free openings that the flow can enter and exit based on buoyancy-induced currents inside the domain.I think I've read each and every one of the relevant threads I found here regarding these types of cases, the most relevant being:Common setup for p_rgh in complete open domainsbuoyantSimpleFoam and watertankCorrect boundary conditions for p_rgh (special for vertical patches)(I seem to remember a couple more threads that had relevant info and that I may have gathered some additional tips, although I cannot seem to find them right now)In the following link you can get my full setup directory for a simple buoyant box:a low opening on the left and a high opening on the rightbottom wall takes a fixed temperature or a heat fluxflow should enter from the left opening (low) and exit through the right opening (high)https://www.dropbox.com/scl/fi/e9x1y...prw7k6vmo&dl=0Short BC info:U:walls noSlipopenings pressureInletOutletVelocityp_rgh:walls fixedFluxPressureopenings prghTotalHydrostaticPressureph_rgh:fixedFluxPressure everywherefunction that initializes ph_rgh in controlDictepsilon|omega|k:wall functions on wallsinletOutlet on openingsT:same as above, with only the bottom wall having a fixedValue or an externalWallHeatFluxTemperature BCOverall things that I've learned trying to run this case:You have to initialize ph_rgh accordingly, because otherwise the fluid will produce flow due its own gravity forceEven  with 0 temperature difference (which should be a domain with 0  velocity), the solver produces some definitely non-zero velocities (they are in the order of magnitude 1e-02)The case needs to be run with buoyantPimpleFoam because buoyantSimpleFoam produces high artificial velocities (even without temperature differences)The thing that bugs me is that the flow takes literally forever to converge into a steadyState-like state. Moreover, I am not quite sure that my setup is correct and I cannot move to more complex cases (which is my final goal).Is this BC setup the best thing we can do in openFOAM? Should I try something different?Attached ImagesU.jpg(27.9 KB, 16 views)T.jpg(27.5 KB, 17 views) |  | U.jpg(27.9 KB, 16 views) |  | T.jpg(27.5 KB, 17 views)\n | U.jpg(27.9 KB, 16 views)\n | T.jpg(27.5 KB, 17 views)\n | \n | U.jpg(27.9 KB, 16 views)\n | T.jpg(27.5 KB, 17 views)\n\nTags\nbuoyancy,natural convection,openfoam,p_rgh\nThread Tools\nShow Printable Version\nDisplay Modes\nLinear Mode\nSwitch to Hybrid Mode\nSwitch to Threaded Mode\nSearch this Thread\n\nAdvanced Search\nPosting RulesYoumay notpost new threadsYoumay notpost repliesYoumay notpost attachmentsYoumay notedit your postsBB codeisOnSmiliesareOn[IMG]code isOnHTML code isOffTrackbacksareOffPingbacksareOnRefbacksareOnForum Rules | Posting Rules | Youmay notpost new threadsYoumay notpost repliesYoumay notpost attachmentsYoumay notedit your postsBB codeisOnSmiliesareOn[IMG]code isOnHTML code isOffTrackbacksareOffPingbacksareOnRefbacksareOnForum Rules |  | \nPosting Rules\nYoumay notpost new threadsYoumay notpost repliesYoumay notpost attachmentsYoumay notedit your postsBB codeisOnSmiliesareOn[IMG]code isOnHTML code isOffTrackbacksareOffPingbacksareOnRefbacksareOnForum Rules\n\nPosting Rules\nYoumay notpost new threadsYoumay notpost repliesYoumay notpost attachmentsYoumay notedit your postsBB codeisOnSmiliesareOn[IMG]code isOnHTML code isOffTrackbacksareOffPingbacksareOnRefbacksareOnForum Rules\n\nSimilar Threads\nThread | Thread Starter | Forum | Replies | Last Post\nHeat transfer between two closed cavities with natural convection | Czarulla | FLUENT | 2 | August 5, 202012:36\nNatural convection in a closed domain STILL NEEDING help! | Yr0gErG | FLUENT | 4 | December 2, 201900:04\nNatural Convection around two spheres in a box - chtMultiRegioSimpleFoam | salvo-K61IC | OpenFOAM | 4 | January 16, 201513:27\nnatural convection at high Rayleigh | mauricio | FLUENT | 2 | February 23, 200519:43\nMixing By Natural Convection Processes | Greg Perkins | FLUENT | 0 | February 12, 200318:40\nContact Us-CFD Online-Privacy Statement-Top\nLinkBack\nLinkBack URL\nAbout LinkBacks\nBookmark & Share\nDigg this Thread!\nAdd Thread to del.icio.us\nBookmark in Technorati\nTweet this thread\n",
#       "images": []
#     }
#   ],
#   "failed_results": [],
#   "response_time": 1.15
# }


# [
#     {
#         'title': 'Icml 2024 顶级论文：机器学习领域的新进展 - Csdn博客', 
#         'href': 'https://blog.csdn.net/Python_cocola/article/details/144093421', 
#         'body': '机器学习的定义和任务 • 机器学习的发展历史 • 机器学习的主要方法 • 机器学习面临的挑战 • 最新发展方向'
#     },
#     {
#         'title': 'PEP307导读：Python 移除 GIL 了!但是换了一种锁... - 知乎', 
#         'href': 'https://zhuanlan.zhihu.com/p/14745776605', 
#         'body': 'PEP 703 正式宣布，从 Python 3.13 起 全局解释器锁 （GIL）将成为可选配置! 一. Intro. 在当下数据科学和 AI 领域，凭借简单易上手的 Python 可谓占据大半江山，然而随着使用的深入，天下苦 GIL 久成为一众研究人员和开发者多么痛的领悟，例如： 数据科学与机器学习： 多核 CPU 在训练模型和数据处理中的潜力难以被充分利用，许多团队（Numpy 、 TensorFlow 等）被迫采用其他语言（如 C++ 或 Rust）来实现核心逻辑，随着而来，开发维护成本直线上升，使用上也有诸多限制。 游戏与图形处理：实时计算与渲染任务中，Python 的多线程能力受到严重抑制，使其难以承担性能要求较高的任务。'
#     }, 
#     {
#         'title': '2025年Python领域最新国际动态与技术趋势解析（截至2025 ...', 
#         'href': 'https://blog.csdn.net/CDMYC/article/details/145516946', 
#         'body': 'OpenAI 近期推出的免费推理模型o3-mini在数学代码生成和物理模拟领域表现突出，尤其在 Python 生态中，开发者可通过API快速集成其能力。 例如，生成符合物理定律的代码（如动态 Shader 或游戏逻辑）时，Python因其简洁性成为首选调用语言。 而谷歌的Gemini 2.0系列（如Pro版本）支持调用谷歌搜索工具和执行代码，这对Python开发者构建数据驱动的AI应用（如自动化科研分析）具有重要意义。 GitHub Copilot X已支持多模态提示生成，可自动为Python模块编写文档，并通过语义搜索优化大型代码库的维护。 例如，输入"快速排序算法"即可生成完整函数，显著提升开发效率。'
#     }, 
#     {
#         'title': '2024年3月最新的深度学习论文推荐 - 知乎', 
#         'href': 'https://zhuanlan.zhihu.com/p/686732702', 
#         'body': '使用迭代学习策略研究语言代理的开放动作学习，该策略使用Python函数来创建和改进动作;在每次迭代中，提出的框架(LearnAct)根据执行反馈对可用动作进行修改和更新，扩大动作空间，提高动作有效性;LearnAct框架在机器人规划和AlfWorld环境中进行了测试'
#     }, 
#     {
#         'title': '探索前沿算法论文：Python与机器学习领域最新研究成果解析', 
#         'href': 'https://www.oryoy.com/news/tan-suo-qian-yan-suan-fa-lun-wen-python-yu-ji-qi-xue-xi-ling-yu-zui-xin-yan-jiu-cheng-guo-jie-xi.html', 
#         'body': '本文将深入解析Python与机器学习领域的最新研究成果，带您一窥这些前沿技术的奥秘。 Python因其简洁易读的语法和强大的库支持，成为了机器学习领域的首选编程语言。 无论是数据预处理、模型训练还是结果可视化，Python都能提供高效的解决方案。 在机器学习中，数据预处理是至关重要的一步。 Python的Pandas库可以高效地处理和分析数据，而Numpy库则提供了强大的数值计算功能。 通过这些工具，研究人员可以快速完成数据清洗、特征提取等任务。 Scikit-Learn是Python中最受欢迎的机器学习库之一，它提供了多种经典的机器学习算法，如线性回归、支持向量机（SVM）和随机森林等。 此外，TensorFlow和PyTorch等深度学习框架也为复杂模型的训练提供了强大的支持。'
#     }
# ]


# {
#   "query": "cfd online OpenFOAM Foam::error:: printStack(",
#   "follow_up_questions": null,
#   "answer": null,
#   "images": [],
#   "results": [
#     {
#       "title": "#0 Foam::error::printStack(Foam::Ostream&) at - CFD Online",
#       "url": "https://www.cfd-online.com/Forums/openfoam-solving/187818-0-foam-error-printstack-foam-ostream.html",
#       "content": "THe problem appears due to the boundary conditions. It may be due to the Pressure outlet, the units are established in Pa and you should take into account a total pressure, not a p/rho (m2/s2) pressure as it is taken in incompressible flow (simpleFoam).",
#       "score": 0.8058924,
#       "raw_content": null
#     },
#     {
#       "title": "Foam::error::printStack(Foam::Ostream&) at - CFD Online",
#       "url": "https://www.cfd-online.com/Forums/openfoam-solving/174378-foam-error-printstack-foam-ostream.html",
#       "content": "Hi all! I'm a Foamer beginner and I hope you can help me. I have been trying to solve a heat transfer case with chtMultiRegionSimpleFoam and kOmegaSST",
#       "score": 0.7325349,
#       "raw_content": null
#     },
#     {
#       "title": "Foam::error::PrintStack -- CFD Online Discussion Forums",
#       "url": "https://www.cfd-online.com/Forums/openfoam-solving/89644-foam-error-printstack.html",
#       "content": "Courant Number mean: 0.256274 max: 3.73333 PIMPLE: Operating solver in PISO mode time step continuity errors : sum local = 0.000307692, global = -1.74165e-05, cumulative = -1.74165e-05 DICPCG: Solving for pcorr, Initial residual = 1, Final residual = 9.01496e-11, No Iterations 589 time step continuity errors : sum local = 4.60233e-10, global",
#       "score": 0.7140107,
#       "raw_content": null
#     },
#     {
#       "title": "Foam::error::printStack(Foam::Ostream&) and Segmentation error ... - Reddit",
#       "url": "https://www.reddit.com/r/OpenFOAM/comments/rdmc5z/foamerrorprintstackfoamostream_and_segmentation/",
#       "content": "I cannot say about the mesh. I have always worked with closed meshes. You might find issues, try to get a closed one if possible. Regarding this particular problem, your \"sides\" boundary is defined as type wall on constant/polymesh/boundary, but you have specified no dsmcPatchBoundary for it.",
#       "score": 0.5035894,
#       "raw_content": null
#     },
#     {
#       "title": "OpenFoam throws error's when running the solver - FreeCAD",
#       "url": "https://forum.freecad.org/viewtopic.php?t=85973",
#       "content": "IMPORTANT: Please click here and read this first, before posting on this CfdOF fourm",
#       "score": 0.4808937,
#       "raw_content": null
#     }
#   ],
#   "response_time": 1.21
# }