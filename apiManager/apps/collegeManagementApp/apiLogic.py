from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

# Django imports
from adminDashboardApp.models import College

# Serializers
from .serializers import CollegeExplorePage


router = APIRouter()


@router.get("/colleges/explore")
async def explore_colleges():

    @sync_to_async
    def get_colleges():
        college_list = []
        for college in College.objects.all():
            college_list.append(
                {
                    "collegeId": college.collegeId,
                    "name": college.name,
                    "campus_image": (
                        college.campus_image.url if college.campus_image else None
                    ),
                    "state": college.state,
                    "city": college.city,
                    "logo": college.logo.url if college.logo else None,
                }
            )
        return college_list
    
    college_data = await get_colleges()
    colleges = [CollegeExplorePage(**college) for college in college_data]
    
    return {"colleges": colleges}
