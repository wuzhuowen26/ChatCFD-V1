import streamlit as st

# markdown
st.markdown('Streamlit Demo')

# 设置网页标题
st.title('一个傻瓜式构建可视化 web的 Python 神器 -- streamlit')

# 展示一级标题
st.header('1. 安装')

st.text('和安装其他包一样，安装 streamlit 非常简单，一条命令即可')
code1 = '''pip3 install streamlit'''
st.code(code1, language='bash')


# 展示一级标题
st.header('2. 使用')

# 展示二级标题
st.subheader('2.1 生成 Markdown 文档')

# 纯文本
st.text('导入 streamlit 后，就可以直接使用 st.markdown() 初始化')

# 展示代码，有高亮效果
code2 = '''import streamlit as st
st.markdown('Streamlit Demo')'''
st.code(code2, language='python')


        # pointField points(19);
        # points[0]  = point(0.5, 0, -0.5); 
        # points[1]  = point(1.5, 0, -0.5); 
        # points[2]  = point(32, 0, -0.5); 
        # points[3]  = point(32, 1.060660, -0.5);         // 1.5/sqrt(2)
        # points[4]  = point(1.060660, 1.060660, -0.5); 
        # points[5]  = point(0.530330, 0.530330, -0.5);   // 1.5/2/sqrt(2)
        # points[6]  = point(32, 7, -0.5);
        # points[7]  = point(1.060660, 7, -0.5);
        # points[8]  = point(0, 7, -0.5);
        # points[9]  = point(0, 1.5, -0.5);
        # points[10] = point(0, 0.5, -0.5);
        # points[11] = point(-0.5, 0, -0.5);
        # points[12] = point(-1.5, 0, -0.5);
        # points[13] = point(-8, 0, -0.5);
        # points[14] = point(-8, 1.060660, -0.5);
        # points[15] = point(-1.060660, 1.060660, -0.5);
        # points[16] = point(-0.530330, 0.530330, -0.5);
        # points[17] = point(-8, 7, -0.5);
        # points[18] = point(-1.060660, 7, -0.5);

/*--------------------------------*- C++ -*----------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  10
     \\/     M anipulation  |
\*---------------------------------------------------------------------------*/
FoamFile
{
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices #codeStream
{
    codeInclude
    #{
        #include "pointField.H"
    #};

    code
    #{
        pointField points(19);
        points[0]  = point(0.5, 0, -0.5);
        points[1]  = point(1.5, 0, -0.5);
        points[2]  = point(32, 0, -0.5);
        points[3]  = point(32, 1.060660, -0.5);
        points[4]  = point(1.060660, 1.060660, -0.5);
        points[5]  = point(0.352553, 0.352553, -0.5);
        points[6]  = point(32, 7, -0.5);
        points[7]  = point(1.060660, 7, -0.5);
        points[8]  = point(0, 7, -0.5);
        points[9]  = point(0, 1.5, -0.5);
        points[10] = point(0, 0.5, -0.5);
        points[11] = point(-0.5, 0, -0.5);
        points[12] = point(-1.5, 0, -0.5);
        points[13] = point(-8, 0, -0.5);
        points[14] = point(-8, 1.060660, -0.5);
        points[15] = point(-1.060660, 1.060660, -0.5);
        points[16] = point(-0.352553, 0.352553, -0.5);
        points[17] = point(-8, 7, -0.5);
        points[18] = point(-1.060660, 7, -0.5);

        points[19] = point(-1.060660, -7, -0.5);
        points[20] = point(-8, -7, -0.5);
        points[21] = point(-0.352553, -0.352553, -0.5);
        points[22] = point(-1.060660, -1.060660, -0.5);
        points[23] = point(-8, -1.060660, -0.5);
        points[24] = point(0, -0.5, -0.5);
        points[25] = point(0, -1.5, -0.5);
        points[26] = point(0, -7, -0.5);
        points[27] = point(1.060660, -7, -0.5);
        points[28] = point(32, -7, -0.5);
        points[29] = point(0.352553, -0.352553, -0.5);
        points[30] = point(1.060660, -1.060660, -0.5);
        points[31] = point(32, -1.060660, -0.5);

        // Duplicate z points
        label sz = points.size();
        points.setSize(2*sz);
        for (label i = 0; i < sz; i++)
        {
            const point& pt = points[i];
            points[i+sz] = point(pt.x(), pt.y(), -pt.z());
        }

        os  << points;
    #};
};


# blocks
# (
#     hex (5 4 9 10 37 26 41 42) (10 10 1) simpleGrading (1 1 1)
#     hex (0 1 4 5 32 33 36 37) (10 10 1) simpleGrading (1 1 1)
#     hex (1 2 3 4 33 34 35 36) (20 10 1) simpleGrading (1 1 1)
#     hex (4 3 6 7 36 35 38 39) (20 20 1) simpleGrading (1 1 1)
#     hex (9 4 7 8 41 36 49 40) (10 20 1) simpleGrading (1 1 1)
#     hex (15 16 10 9 47 48 42 41) (10 10 1) simpleGrading (1 1 1)
#     hex (12 11 16 15 44 43 48 47) (10 10 1) simpleGrading (1 1 1)
#     hex (13 12 15 14 45 44 47 36) (20 10 1) simpleGrading (1 1 1)
#     hex (14 15 18 17 46 47 50 49) (20 20 1) simpleGrading (1 1 1)
#     hex (15 9 8 18 47 41 40 50) (10 20 1) simpleGrading (1 1 1)

#     hex (29 30 24 21 61 62 56 53) (10 10 1) simpleGrading (1 1 1)
#     hex (0 1 30 29 32 33 62 61) (10 10 1) simpleGrading (1 1 1)
#     hex (1 2 31 30 33 34 63 62) (20 10 1) simpleGrading (1 1 1)
#     hex (30 31 28 27 62 63 60 59) (20 20 1) simpleGrading (1 1 1)
#     hex (25 30 27 26 57 62 59 58) (10 20 1) simpleGrading (1 1 1)
#     hex (22 21 24 25 54 53 56 57) (10 10 1) simpleGrading (1 1 1)
#     hex (12 11 21 22 44 43 53 54) (10 10 1) simpleGrading (1 1 1)
#     hex (13 12 22 23 45 44 54 55) (20 10 1) simpleGrading (1 1 1)
#     hex (23 22 19 20 55 54 51 52) (20 20 1) simpleGrading (1 1 1)
#     hex (22 25 26 19 54 57 58 51) (10 20 1) simpleGrading (1 1 1)
# );

# edges
# (
#     arc 0 5 45.0 (0 0 1)
#     arc 5 10 45.0 (0 0 1)
#     arc 1 4 45.0 (0 0 1)
#     arc 4 9 45.0 (0 0 1)
#     arc 32 37 45.0 (0 0 1)
#     arc 37 42 45.0 (0 0 1)
#     arc 33 26 45.0 (0 0 1)
#     arc 36 41 45.0 (0 0 1)

#     arc 11 16 45.0 (0 0 -1)
#     arc 16 10 45.0 (0 0 -1)
#     arc 12 15 45.0 (0 0 -1)
#     arc 15 9 45.0 (0 0 -1)
#     arc 43 48 45.0 (0 0 -1)
#     arc 38 42 45.0 (0 0 -1)
#     arc 44 37 45.0 (0 0 -1)
#     arc 37 41 45.0 (0 0 -1)

#     arc 29 0 45.0 (0 0 1)
#     arc 24 29 45.0 (0 0 1)
#     arc 30 1 45.0 (0 0 1)
#     arc 25 30 45.0 (0 0 1)
#     arc 61 32 45.0 (0 0 1)
#     arc 56 61 45.0 (0 0 1)
#     arc 62 33 45.0 (0 0 1)
#     arc 57 62 45.0 (0 0 1)

#     arc 21 11 45.0 (0 0 -1)
#     arc 24 21 45.0 (0 0 -1)
#     arc 22 12 45.0 (0 0 -1)
#     arc 25 22 45.0 (0 0 -1)
#     arc 53 42 45.0 (0 0 -1)
#     arc 56 53 45.0 (0 0 -1)
#     arc 54 44 45.0 (0 0 -1)
#     arc 57 54 45.0 (0 0 -1)
# );

# defaultPatch
# {
#     type empty;
# }

# boundary
# (
#     down
#     {
#         type symmetryPlane;
#         faces
#         (
#             (20 19 51 52)
#             (19 26 58 51)
#             (26 27 59 58)
#             (27 28 60 59)
#         );
#     }
#     right
#     {
#         type patch;
#         faces
#         (
#             (2 3 35 34)
#             (3 6 38 35)
#             (31 2 34 63)
#             (28 31 63 60)
#         );
#     }
#     up
#     {
#         type symmetryPlane;
#         faces
#         (
#             (7 8 40 39)
#             (6 7 39 38)
#             (8 18 50 40)
#             (18 17 49 50)
#         );
#     }
#     left
#     {
#         type patch;
#         faces
#         (
#             (14 13 45 46)
#             (17 14 46 49)
#             (23 13 42 55)
#             (20 23 55 52)
#         );
#     }
#     cylinder
#     {
#         type symmetry;
#         faces
#         (
#             (10 5 37 42)
#             (5 0 32 37)
#             (16 10 42 48)
#             (11 16 48 43)
#             (11 21 53 43)
#             (21 24 56 53)
#             (24 29 61 56)
#             (29 0 32 61)
#         );
#     }
# );

